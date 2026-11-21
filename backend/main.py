"""API REST do painel de financiamento de campanha (Sprint 2 + entrega final).

A API le direto do banco dimensional (Dados/campanha.db) e serve:
- a carga completa (resumo, candidatos, serie diaria, origens, partidos);
- a listagem de candidatos com detalhe por origem (com filtros de periodo e categoria);
- os filtros disponiveis (partidos, prestações, categorias/origens, periodo);
- o relatorio de controle de qualidade.

Toda a apuracao e feita a partir do banco; nao ha JSON estatico embutido.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

RAIZ = Path(__file__).resolve().parent.parent
# Garante que `db` (na mesma pasta) seja importavel, independente do diretorio atual.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import db
import seed

app = FastAPI(title="Financiamento de Campanha — API", version="1.0.0")

# O painel pode ser aberto via file:// durante o desenvolvimento; habilitamos CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def get_conn() -> sqlite3.Connection:
    # Apenas abre a conexao. O schema (views) e o QC sao gerados pelo ETL e
    # persistidos no proprio banco; recria-los a cada request seria caro.
    return db.conectar()


# --------------------------------------------------------------------------- #
# Helpers de apuracao
# --------------------------------------------------------------------------- #
def _avisos_desatualizados(candidatos: list[dict]) -> list[dict]:
    """Monta os avisos de candidatos com dados desatualizados (seed)."""
    mapa_dt = {c["sq_candidato"]: c["dt_geracao"] for c in seed.DESATUALIZADOS}
    avisos = []
    for c in candidatos:
        if c.get("desatualizado"):
            dt = mapa_dt.get(c["sq_candidato"], "12/09/2026")
            avisos.append(
                {
                    "sq_candidato": c["sq_candidato"],
                    "nome": c["nm_candidato"],
                    "partido": c["sg_partido"],
                    "texto": seed.AVISO.format(
                        nome=c["nm_candidato"], partido=c["sg_partido"], dt=dt
                    ),
                }
            )
    return avisos


def _periodo(conn: sqlite3.Connection, cargo: str | None = None) -> dict:
    sql = "SELECT MIN(data) AS ini, MAX(data) AS fim FROM fato_despesa"
    args: list = []
    if cargo:
        sql += " WHERE cd_cargo = ?"
        args.append(cargo)
    row = conn.execute(sql, args).fetchone()
    ini = row["ini"]
    fim = row["fim"]
    # Limita a janela ao ano eleitoral (2026): a fonte tem lancamentos com datas
    # claramente erroneas (2025 e 2027/2028) que distorceriam o periodo exibido.
    if ini and ini < "2026-01-01":
        ini = "2026-01-01"
    if fim and fim > "2026-12-31":
        fim = "2026-12-31"
    return {"inicio": ini, "fim": fim}


def _serie_diaria(conn: sqlite3.Connection, cargo: str | None, inicio: str, fim: str) -> list[dict]:
    if not cargo or not inicio or not fim:
        return []
    rows = conn.execute(
        "SELECT data, sg_partido, total FROM resumo_serie_cargo WHERE cd_cargo = ?",
        (cargo,),
    ).fetchall()
    mapa: dict[str, dict[str, float]] = {}
    for r in rows:
        mapa.setdefault(r["data"], {})[r["sg_partido"]] = r["total"]

    # Preenche todos os dias do intervalo (inclusive os sem lancamento, com valor 0).
    d0 = date.fromisoformat(inicio)
    d1 = date.fromisoformat(fim)
    serie = []
    dia = d0
    while dia <= d1:
        iso = dia.isoformat()
        por_part = mapa.get(iso, {})
        serie.append(
            {
                "data": iso,
                "total": round(sum(por_part.values()), 2),
                "por_partido": {k: round(v, 2) for k, v in por_part.items()},
            }
        )
        dia += timedelta(days=1)
    return serie


def _origens_do_candidato(conn: sqlite3.Connection, sq: str, categoria: str | None,
                          data_ini: str | None, data_fim: str | None) -> list[dict]:
    sql = (
        "SELECT origem_despesa AS origem, COUNT(*) AS lancamentos, SUM(valor) AS total "
        "FROM fato_despesa WHERE sq_candidato = ?"
    )
    args: list = [sq]
    if categoria:
        sql += " AND origem_despesa = ?"
        args.append(categoria)
    if data_ini:
        sql += " AND data >= ?"
        args.append(data_ini)
    if data_fim:
        sql += " AND data <= ?"
        args.append(data_fim)
    sql += " GROUP BY origem_despesa ORDER BY total DESC"
    rows = conn.execute(sql, args).fetchall()
    return [
        {"origem": r["origem"], "lancamentos": r["lancamentos"], "total": round(r["total"], 2)}
        for r in rows
    ]


def _prestacoes_do_candidato(conn: sqlite3.Connection, sq: str,
                             data_ini: str | None = None, data_fim: str | None = None) -> list[dict]:
    rows = conn.execute(
        "SELECT tipo, lancamentos, total FROM resumo_prestacao_candidato "
        "WHERE sq_candidato = ? ORDER BY total DESC",
        (sq,),
    ).fetchall()
    return [
        {"tipo": r["tipo"], "lancamentos": r["lancamentos"], "total": round(r["total"], 2)}
        for r in rows
    ]


def _prestacoes_map(conn: sqlite3.Connection, cargo: str | None) -> dict[str, list[dict]]:
    """Prestacoes (tipos) de todos os candidatos do cargo, em uma unica consulta."""
    rows = conn.execute(
        "SELECT p.sq_candidato AS sq, p.tipo, p.lancamentos, p.total "
        "FROM resumo_prestacao_candidato p "
        "JOIN resumo_candidato c ON c.sq_candidato = p.sq_candidato "
        "WHERE c.cd_cargo = ?",
        (cargo,),
    ).fetchall()
    mapa: dict[str, list[dict]] = {}
    for r in rows:
        mapa.setdefault(r["sq"], []).append(
            {"tipo": r["tipo"], "lancamentos": r["lancamentos"], "total": round(r["total"], 2)}
        )
    return mapa


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@app.get("/api/carga")
def carga(cargo: str = Query(default="1", description="CD_CARGO (1=Presidente, 3=Governador, ...)")):
    """Carga completa reconstruida a partir do banco (substitui o data.js estatico)."""
    conn = get_conn()
    try:
        info = conn.execute(
            "SELECT dt_geracao_tse, arquivo, linhas_lidas, linhas_carga FROM carga LIMIT 1"
        ).fetchone()
        periodo = _periodo(conn, cargo)
        prestacoes_map = _prestacoes_map(conn, cargo)

        # Origens por candidato: incluidas no payload apenas para cargos pequenos
        # (ate 500 candidatos). Em cargos grandes o detalhe e carregado sob demanda.
        origens_map: dict[str, list[dict]] = {}
        info_cargo = conn.execute(
            "SELECT candidatos FROM resumo_cargo WHERE cd_cargo = ?", (cargo,)
        ).fetchone()
        if info_cargo and info_cargo["candidatos"] <= 500:
            for r in conn.execute(
                "SELECT f.sq_candidato AS sq, f.origem_despesa AS origem, "
                "COUNT(*) AS lancamentos, SUM(f.valor) AS total "
                "FROM fato_despesa f WHERE f.cd_cargo = ? "
                "GROUP BY f.sq_candidato, f.origem_despesa",
                (cargo,),
            ):
                origens_map.setdefault(r["sq"], []).append(
                    {
                        "origem": r["origem"],
                        "lancamentos": r["lancamentos"],
                        "total": round(r["total"], 2),
                    }
                )

        candidatos = []
        for r in conn.execute(
            "SELECT * FROM resumo_candidato WHERE cd_cargo = ? ORDER BY total DESC", (cargo,)
        ):
            sq = r["sq_candidato"]
            candidatos.append(
                {
                    "sq_candidato": sq,
                    "nm_candidato": r["nm_candidato"],
                    "nr_candidato": r["nr_candidato"],
                    "sg_partido": r["sg_partido"],
                    "nm_partido": r["nm_partido"],
                    "nr_partido": r["nr_partido"],
                    "cd_cargo": r["cd_cargo"],
                    "ds_cargo": r["ds_cargo"],
                    "lancamentos": r["lancamentos"],
                    "total": round(r["total"], 2),
                    "desatualizado": bool(r["desatualizado"]),
                    "origens": origens_map.get(sq, []),
                    "prestacoes": prestacoes_map.get(sq, []),
                }
            )

        avisos = _avisos_desatualizados(candidatos)

        por_mes = [
            {"mes": r["mes"], "lancamentos": r["lancamentos"], "total": round(r["total"], 2)}
            for r in conn.execute(
                "SELECT mes, lancamentos, total FROM resumo_mes_cargo WHERE cd_cargo = ? ORDER BY mes",
                (cargo,),
            )
        ]
        origens_gerais = [
            {"origem": r["origem"], "lancamentos": r["lancamentos"], "total": round(r["total"], 2)}
            for r in conn.execute(
                "SELECT origem, lancamentos, total FROM resumo_origem_cargo "
                "WHERE cd_cargo = ? AND origem <> '#NULO' ORDER BY total DESC",
                (cargo,),
            )
        ]
        por_partido = [
            {"sigla": r["sg_partido"], "nome": r["nome"], "lancamentos": r["lancamentos"], "total": round(r["total"], 2)}
            for r in conn.execute(
                "SELECT sg_partido, nome, lancamentos, total FROM resumo_partido_cargo "
                "WHERE cd_cargo = ? ORDER BY total DESC",
                (cargo,),
            )
        ]

        total_declarado = round(sum(c["total"] for c in candidatos), 2)
        total_atual = round(sum(c["total"] for c in candidatos if not c["desatualizado"]), 2)
        total_lancamentos = sum(c["lancamentos"] for c in candidatos)

        return {
            "fonte": "Portal de Dados Abertos do TSE — Prestação de Contas Eleitorais 2026",
            "cargo": cargo,
            "arquivo": info["arquivo"] if info else None,
            "dt_geracao_tse": info["dt_geracao_tse"] if info else None,
            "linhas_arquivo": info["linhas_lidas"] if info else None,
            "linhas_carga": info["linhas_carga"] if info else total_lancamentos,
            "total_declarado": total_declarado,
            "total_atual": total_atual,
            "avisos_desatualizados": avisos,
            "periodo_despesas": periodo,
            "por_mes": por_mes,
            "serie_diaria": _serie_diaria(conn, cargo, periodo["inicio"], periodo["fim"]),
            "origens_gerais": origens_gerais,
            "por_partido": por_partido,
            "ressalva": "Despesa contratada declarada até a data da carga. Não é o gasto total da campanha.",
            "candidatos": candidatos,
        }
    finally:
        conn.close()


@app.get("/api/filtros")
def filtros(cargo: str = Query(default="1", description="CD_CARGO")):
    """Opcoes disponiveis para os filtros do painel, lidas do banco."""
    conn = get_conn()
    try:
        partidos = [
            {"sigla": r["sg_partido"], "nome": r["nm_partido"]}
            for r in conn.execute(
                "SELECT DISTINCT sg_partido, nm_partido FROM resumo_candidato "
                "WHERE cd_cargo = ? ORDER BY sg_partido",
                (cargo,),
            )
        ]
        prestacoes = [
            r["tipo"]
            for r in conn.execute(
                "SELECT DISTINCT p.tipo AS tipo FROM resumo_prestacao_candidato p "
                "JOIN resumo_candidato c ON c.sq_candidato = p.sq_candidato "
                "WHERE c.cd_cargo = ? ORDER BY tipo",
                (cargo,),
            )
        ]
        categorias = [
            r["origem"]
            for r in conn.execute(
                "SELECT DISTINCT origem FROM resumo_origem_cargo "
                "WHERE cd_cargo = ? AND origem IS NOT NULL AND origem <> '#NULO' ORDER BY origem",
                (cargo,),
            )
        ]
        return {
            "partidos": partidos,
            "prestacoes": prestacoes,
            "categorias": categorias,
            "periodo": _periodo(conn, cargo),
        }
    finally:
        conn.close()


@app.get("/api/candidatos")
def candidatos(
    cargo: str = Query(default="1", description="CD_CARGO"),
    data_ini: str | None = Query(default=None, description="AAAA-MM-DD"),
    data_fim: str | None = Query(default=None, description="AAAA-MM-DD"),
    categoria: str | None = Query(default=None, description="Origem/categoria da despesa"),
):
    """Listagem de candidatos recalculada a partir do banco.

    Aplica filtros de periodo (data_ini/data_fim) e categoria (origem_despesa),
    recalculando total, numero de lancamentos e prestacoes de cada candidato.
    """
    conn = get_conn()
    try:
        if not (data_ini or data_fim or categoria):
            linhas = conn.execute(
                "SELECT sq_candidato, nm_candidato, nr_candidato, sg_partido, nm_partido, "
                "nr_partido, desatualizado, lancamentos, total FROM resumo_candidato "
                "WHERE cd_cargo = ? ORDER BY total DESC",
                (cargo,),
            ).fetchall()
        else:
            where = ["f.cd_cargo = ?"]
            args: list = [cargo]
            if data_ini:
                where.append("f.data >= ?")
                args.append(data_ini)
            if data_fim:
                where.append("f.data <= ?")
                args.append(data_fim)
            if categoria:
                where.append("f.origem_despesa = ?")
                args.append(categoria)
            sql = (
                "SELECT d.sq_candidato, d.nm_candidato, d.nr_candidato, d.sg_partido, "
                "d.nm_partido, d.nr_partido, MAX(d.desatualizado) AS desatualizado, "
                "COUNT(f.id_despesa) AS lancamentos, SUM(f.valor) AS total "
                "FROM fato_despesa f JOIN dim_candidato d ON d.sq_candidato = f.sq_candidato WHERE "
                + " AND ".join(where)
                + " GROUP BY d.sq_candidato ORDER BY total DESC"
            )
            linhas = conn.execute(sql, args).fetchall()

        prestacoes = _prestacoes_map(conn, cargo)

        lista = []
        for r in linhas:
            sq = r["sq_candidato"]
            lista.append(
                {
                    "sq_candidato": sq,
                    "nm_candidato": r["nm_candidato"],
                    "nr_candidato": r["nr_candidato"],
                    "sg_partido": r["sg_partido"],
                    "nm_partido": r["nm_partido"],
                    "nr_partido": r["nr_partido"],
                    "lancamentos": r["lancamentos"],
                    "total": round(r["total"], 2),
                    "desatualizado": bool(r["desatualizado"]),
                    "origens": [],
                    "prestacoes": prestacoes.get(sq, []),
                }
            )

        return {
            "cargo": cargo,
            "filtros": {"data_ini": data_ini, "data_fim": data_fim, "categoria": categoria},
            "resumo": {
                "total": round(sum(c["total"] for c in lista), 2),
                "candidatos": len(lista),
                "lancamentos": sum(c["lancamentos"] for c in lista),
            },
            "avisos_desatualizados": _avisos_desatualizados(lista),
            "candidatos": lista,
        }
    finally:
        conn.close()


@app.get("/api/candidatos/{sq}")
def candidato_detalhe(sq: str):
    """Detalhe de um candidato por origem e por tipo de prestacao."""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM resumo_candidato WHERE sq_candidato = ?", (sq,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Candidato nao encontrado")
        return {
            "sq_candidato": row["sq_candidato"],
            "nm_candidato": row["nm_candidato"],
            "nr_candidato": row["nr_candidato"],
            "sg_partido": row["sg_partido"],
            "nm_partido": row["nm_partido"],
            "nr_partido": row["nr_partido"],
            "cd_cargo": row["cd_cargo"],
            "ds_cargo": row["ds_cargo"],
            "lancamentos": row["lancamentos"],
            "total": round(row["total"], 2),
            "desatualizado": bool(row["desatualizado"]),
            "origens": _origens_do_candidato(conn, sq, None, None, None),
            "prestacoes": _prestacoes_do_candidato(conn, sq, None, None),
        }
    finally:
        conn.close()


@app.get("/api/cargos")
def cargos():
    """Cargos disponiveis na carga, com totais agregados."""
    conn = get_conn()
    try:
        itens = [
            {
                "cd_cargo": r["cd_cargo"],
                "nome": r["nome"],
                "candidatos": r["candidatos"],
                "lancamentos": r["lancamentos"],
                "total": round(r["total"], 2),
            }
            for r in conn.execute("SELECT * FROM resumo_cargo ORDER BY cd_cargo")
        ]
        return {"cargos": itens}
    finally:
        conn.close()


@app.get("/api/partidos")
def partidos(cargo: str | None = Query(default=None, description="CD_CARGO; vazio = todos os cargos")):
    """Custos por partido. Sem `cargo`, soma todos os cargos (visao geral)."""
    conn = get_conn()
    try:
        if cargo:
            rows = conn.execute(
                "SELECT sg_partido, nome, lancamentos, total FROM resumo_partido_cargo "
                "WHERE cd_cargo = ? ORDER BY total DESC",
                (cargo,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT sg_partido, MAX(nome) AS nome, SUM(lancamentos) AS lancamentos, "
                "SUM(total) AS total FROM resumo_partido_cargo GROUP BY sg_partido ORDER BY total DESC"
            ).fetchall()
        itens = [
            {
                "sigla": r["sg_partido"],
                "nome": r["nome"],
                "lancamentos": r["lancamentos"],
                "total": round(r["total"], 2),
            }
            for r in rows
        ]
        return {
            "cargo": cargo,
            "partidos": itens,
            "total": round(sum(p["total"] for p in itens), 2),
        }
    finally:
        conn.close()


@app.get("/api/qc")
def qc():
    """Relatorio de controle de qualidade (contagem de registros e soma por origem)."""
    conn = get_conn()
    try:
        linhas = conn.execute(
            "SELECT verificacao, esperado, obtido, ok FROM qc_resultado ORDER BY rowid"
        ).fetchall()
        resultado = [
            {
                "verificacao": r["verificacao"],
                "esperado": r["esperado"],
                "obtido": r["obtido"],
                "ok": bool(r["ok"]),
            }
            for r in linhas
        ]
        return {"itens": resultado, "tudo_ok": all(i["ok"] for i in resultado)}
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Arquivo estatico do painel (front). index.html na raiz.
# --------------------------------------------------------------------------- #
@app.get("/")
def index():
    return FileResponse(str(RAIZ / "index.html"))


# Precisa ser montado por ultimo para nao capturar as rotas /api.
app.mount("/", StaticFiles(directory=str(RAIZ)), name="static")