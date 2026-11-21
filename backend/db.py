"""Camada de acesso ao banco (SQLite) do painel de financiamento de campanha.

Responsabilidades:
- abrir a conexao com o banco dimensional (Dados/campanha.db);
- garantir que as views de apoio existam (aplica backend/schema.sql);
- rodar o controle de qualidade (contagem de registros e soma por origem),
  gravando o resultado na tabela qc_resultado e devolvendo em memoria.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DB_PATH = RAIZ / "Dados" / "campanha.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def conectar(create: bool = False) -> sqlite3.Connection:
    if not DB_PATH.exists():
        if not create:
            raise FileNotFoundError(
                f"Banco nao encontrado em {DB_PATH}. Rode o ETL (backend/etl.py) "
                "ou restaure o arquivo campanha.db."
            )
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def aplicar_schema(conn: sqlite3.Connection) -> None:
    """Cria (ou recria) as views de apoio. Seguro para rodar em toda inicializacao."""
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def garantir_qc(conn: sqlite3.Connection) -> list[dict]:
    """Tabela de controle de qualidade da carga, recriada a cada execucao."""
    conn.executescript(
        """
        DROP TABLE IF EXISTS qc_resultado;
        CREATE TABLE qc_resultado (
            verificacao TEXT,
            esperado    TEXT,
            obtido      TEXT,
            ok          INTEGER
        );
        """
    )

    carga = conn.execute(
        "SELECT linhas_lidas, linhas_carga FROM carga LIMIT 1"
    ).fetchone()
    linhas_carga_esperado = carga["linhas_carga"] if carga else None

    fato_linhas_atual = conn.execute(
        "SELECT COUNT(*) FROM fato_despesa WHERE desatualizado = 0"
    ).fetchone()[0]
    fato_soma_atual = conn.execute(
        "SELECT COALESCE(SUM(valor),0) FROM fato_despesa WHERE desatualizado = 0"
    ).fetchone()[0]
    fato_soma_todos = conn.execute("SELECT COALESCE(SUM(valor),0) FROM fato_despesa").fetchone()[0]
    soma_por_origem = conn.execute("SELECT COALESCE(SUM(total),0) FROM vw_origem_total").fetchone()[0]
    desatualizados = conn.execute(
        "SELECT COUNT(*) FROM dim_candidato WHERE desatualizado = 1"
    ).fetchone()[0]
    candidatos = conn.execute("SELECT COUNT(*) FROM dim_candidato").fetchone()[0]
    candidatos_na_fato = conn.execute(
        "SELECT COUNT(DISTINCT sq_candidato) FROM fato_despesa"
    ).fetchone()[0]

    # A carga declara o total esperado (total_declarado) e o numero de lancamentos
    # de presidente (apenas a carga atual, sem os seeds desatualizados).
    total_esperado = None
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(carga)")}
    if "total_declarado" in cols and carga is not None:
        total_esperado = conn.execute("SELECT total_declarado FROM carga LIMIT 1").fetchone()[0]

    linhas = []

    ok_linhas = linhas_carga_esperado is not None and fato_linhas_atual == linhas_carga_esperado
    linhas.append(
        {
            "verificacao": "Lancamentos atuais (sem desatualizados) == carga.linhas_carga",
            "esperado": linhas_carga_esperado,
            "obtido": fato_linhas_atual,
            "ok": bool(ok_linhas),
        }
    )

    if total_esperado is not None:
        ok_soma = round(float(total_esperado), 2) == round(float(fato_soma_atual), 2)
        linhas.append(
            {
                "verificacao": "Soma atual (sem desatualizados) == carga.total_declarado",
                "esperado": round(float(total_esperado), 2),
                "obtido": round(float(fato_soma_atual), 2),
                "ok": bool(ok_soma),
            }
        )

    ok_consist = round(float(fato_soma_todos), 2) == round(float(soma_por_origem), 2)
    linhas.append(
        {
            "verificacao": "Soma por origem (vw_origem_total) == soma total de fato_despesa",
            "esperado": round(float(fato_soma_todos), 2),
            "obtido": round(float(soma_por_origem), 2),
            "ok": bool(ok_consist),
        }
    )

    linhas.append(
        {
            "verificacao": "Candidatos distintos na fato == linhas em dim_candidato",
            "esperado": candidatos_na_fato,
            "obtido": candidatos,
            "ok": candidatos_na_fato == candidatos,
        }
    )

    linhas.append(
        {
            "verificacao": "Candidatos desatualizados (seed) so para exibicao",
            "esperado": ">= 0",
            "obtido": desatualizados,
            "ok": True,
        }
    )

    conn.executemany(
        "INSERT INTO qc_resultado (verificacao, esperado, obtido, ok) VALUES (:verificacao, :esperado, :obtido, :ok)",
        [
            {
                "verificacao": l["verificacao"],
                "esperado": str(l["esperado"]),
                "obtido": str(l["obtido"]),
                "ok": 1 if l["ok"] else 0,
            }
            for l in linhas
        ],
    )
    conn.commit()
    return linhas


def inicializar(conn: sqlite3.Connection | None = None) -> sqlite3.Connection:
    """Aplica schema + QC. Usado na inicializacao da API."""
    own = conn is None
    conn = conn or conectar()
    aplicar_schema(conn)
    garantir_qc(conn)
    return conn


if __name__ == "__main__":
    c = inicializar()
    print("QC:")
    for row in c.execute("SELECT verificacao, esperado, obtido, ok FROM qc_resultado"):
        status = "OK" if row["ok"] else "FALHOU"
        print(f"  [{status}] {row['verificacao']} -> esperado={row['esperado']} obtido={row['obtido']}")
    c.close()