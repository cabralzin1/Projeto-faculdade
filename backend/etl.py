"""ETL da prestacao de contas eleitorais (despesas contratadas por candidato).

Fonte correta: `despesas_contratadas_candidatos_2026_BRASIL.csv` (consolidado
BRASIL, por candidato). Por padrao ingere TODOS os cargos (CD_CARGO) e
(re)constroi o banco dimensional Dados/campanha.db. Use `--cargo 1` para
restringir a um cargo.

Uso:
    python backend/etl.py --csv "caminho/despesas_contratadas_candidatos_2026_BRASIL.csv"
    python backend/etl.py --csv ... --cargo 1 --dt-geracao 21/11/2026

Colunas usadas (53 no total):
- DT_GERACAO, TP_PRESTACAO_CONTAS (Final/Parcial), DT_PRESTACAO_CONTAS
- CD_CARGO, DS_CARGO
- SQ_CANDIDATO, NR_CANDIDATO, NM_CANDIDATO, NR_PARTIDO, SG_PARTIDO, NM_PARTIDO
- DS_TIPO_FORNECEDOR, DS_CNAE_FORNECEDOR, NR_CPF_CNPJ_FORNECEDOR, NM_FORNECEDOR,
  NM_FORNECEDOR_RFB, SG_UF_FORNECEDOR, NM_MUNICIPIO_FORNECEDOR
- DS_TIPO_DOCUMENTO, NR_DOCUMENTO, CD_ORIGEM_DESPESA, DS_ORIGEM_DESPESA
- SQ_DESPESA, DT_DESPESA, DS_DESPESA, VR_DESPESA_CONTRATADA (formato BR: 1234,56)
"""
from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import db

NULO = "#NULO#"


def _num(br: str) -> float:
    s = (br or "").strip()
    if s in ("", "#NULO", "#NULO#"):
        return 0.0
    if "," in s and "." in s:  # 1.234,56
        return float(s.replace(".", "").replace(",", "."))
    if "," in s:  # 1234,56
        return float(s.replace(",", "."))
    return float(s)  # 1234.56 ou inteiro


def _data_iso(br: str) -> str:
    s = (br or "").strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return NULO


def _detectar(path: Path):
    amostra = path.read_bytes()[:8192]
    for enc in ("utf-8-sig", "latin-1", "cp1252"):
        try:
            texto = amostra.decode(enc)
            break
        except UnicodeDecodeError:
            texto = None
    enc = enc if texto is not None else "latin-1"
    try:
        sep = csv.Sniffer().sniff(texto[:4096], delimiters=";,\t").delimiter
    except csv.Error:
        sep = ";"
    return enc, sep


def reconstruir(csv_path: Path, cargo: str, dt_geracao_arg: str) -> None:
    enc, sep = _detectar(csv_path)
    print(f"Lendo {csv_path} (encoding={enc}, sep='{sep}')")

    conn = db.conectar(create=True)
    cur = conn.cursor()
    cur.executescript(
        """
        DROP VIEW IF EXISTS vw_candidato_total;
        DROP VIEW IF EXISTS vw_partido_total;
        DROP VIEW IF EXISTS vw_origem_total;
        DROP VIEW IF EXISTS vw_candidato_origem;
        DROP VIEW IF EXISTS vw_candidato_prestacao;
        DROP VIEW IF EXISTS vw_prestacao_total;
        DROP VIEW IF EXISTS vw_serie_diaria;
        DROP VIEW IF EXISTS vw_mes_total;
        DROP TABLE IF EXISTS fato_despesa;
        DROP TABLE IF EXISTS dim_fornecedor;
        DROP TABLE IF EXISTS dim_candidato;
        DROP TABLE IF EXISTS dim_tempo;
        DROP TABLE IF EXISTS carga;
        CREATE TABLE carga (
            executada_em      TEXT,
            dt_geracao_tse    TEXT,
            arquivo           TEXT,
            linhas_lidas      INTEGER,
            linhas_carga      INTEGER,
            total_declarado   REAL
        );
        CREATE TABLE dim_candidato (
            sq_candidato   TEXT PRIMARY KEY,
            nm_candidato   TEXT NOT NULL,
            nr_candidato   TEXT,
            sg_partido     TEXT,
            nm_partido     TEXT,
            nr_partido     TEXT,
            cd_cargo       TEXT,
            ds_cargo       TEXT,
            desatualizado  INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE dim_fornecedor (
            id_fornecedor      INTEGER PRIMARY KEY AUTOINCREMENT,
            cpf_cnpj           TEXT UNIQUE,
            nm_fornecedor      TEXT,
            nm_receita_federal TEXT,
            tipo               TEXT,
            cnae               TEXT,
            uf                 TEXT,
            municipio          TEXT
        );
        CREATE TABLE dim_tempo (
            data   TEXT PRIMARY KEY,
            ano    INTEGER,
            mes    INTEGER,
            dia    INTEGER,
            semana INTEGER
        );
        CREATE TABLE fato_despesa (
            id_despesa     INTEGER PRIMARY KEY AUTOINCREMENT,
            sq_despesa     TEXT,
            tp_prestacao   TEXT,
            sq_candidato   TEXT REFERENCES dim_candidato(sq_candidato),
            cd_cargo       TEXT,
            id_fornecedor  INTEGER REFERENCES dim_fornecedor(id_fornecedor),
            data           TEXT REFERENCES dim_tempo(data),
            origem_despesa TEXT,
            descricao      TEXT,
            tipo_documento TEXT,
            nr_documento   TEXT,
            turno          TEXT,
            dt_prestacao   TEXT,
            valor          REAL NOT NULL,
            desatualizado  INTEGER NOT NULL DEFAULT 0
        );
        """
    )

    candidatos_inseridos: set[str] = set()
    fornecedores: dict[str, int] = {}
    total = 0.0
    n_carga = 0
    n_lidas = 0
    dt_geracao = dt_geracao_arg
    primeira = True

    with csv_path.open("r", encoding=enc, newline="") as fh:
        for row in csv.DictReader(fh, delimiter=sep):
            n_lidas += 1
            if primeira:
                dt_geracao = dt_geracao or row.get("DT_GERACAO", NULO)
                primeira = False

            if cargo and (row.get("CD_CARGO") or "").strip() != cargo:
                continue

            sq = (row.get("SQ_CANDIDATO") or "").strip()
            if not sq or sq in ("#NULO", "-1"):
                continue
            cd_cargo = (row.get("CD_CARGO") or NULO).strip()
            n_carga += 1

            if sq not in candidatos_inseridos:
                cur.execute(
                    "INSERT OR IGNORE INTO dim_candidato "
                    "(sq_candidato, nm_candidato, nr_candidato, sg_partido, nm_partido, nr_partido, cd_cargo, ds_cargo, desatualizado) "
                    "VALUES (?,?,?,?,?,?,?,?,0)",
                    (
                        sq,
                        row.get("NM_CANDIDATO") or NULO,
                        row.get("NR_CANDIDATO") or NULO,
                        row.get("SG_PARTIDO") or NULO,
                        row.get("NM_PARTIDO") or NULO,
                        row.get("NR_PARTIDO") or NULO,
                        (row.get("CD_CARGO") or NULO),
                        (row.get("DS_CARGO") or NULO),
                    ),
                )
                candidatos_inseridos.add(sq)

            cpf = (row.get("NR_CPF_CNPJ_FORNECEDOR") or NULO).strip() or NULO
            if cpf in fornecedores:
                id_forn = fornecedores[cpf]
            else:
                cur.execute(
                    "INSERT OR IGNORE INTO dim_fornecedor "
                    "(cpf_cnpj, nm_fornecedor, nm_receita_federal, tipo, cnae, uf, municipio) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (
                        cpf,
                        row.get("NM_FORNECEDOR") or NULO,
                        row.get("NM_FORNECEDOR_RFB") or row.get("NM_FORNECEDOR") or NULO,
                        row.get("DS_TIPO_FORNECEDOR") or NULO,
                        row.get("DS_CNAE_FORNECEDOR") or NULO,
                        row.get("SG_UF_FORNECEDOR") or NULO,
                        row.get("NM_MUNICIPIO_FORNECEDOR") or NULO,
                    ),
                )
                id_forn = cur.lastrowid
                fornecedores[cpf] = id_forn

            data = _data_iso(row.get("DT_DESPESA") or NULO)
            if data == NULO:
                data = _data_iso(row.get("DT_PRESTACAO_CONTAS") or dt_geracao)
            if data != NULO:
                ano, mes, dia = (int(x) for x in data.split("-"))
                semana = datetime(ano, mes, dia).isocalendar()[1]
                cur.execute(
                    "INSERT OR IGNORE INTO dim_tempo (data, ano, mes, dia, semana) VALUES (?,?,?,?,?)",
                    (data, ano, mes, dia, semana),
                )

            valor = _num(row.get("VR_DESPESA_CONTRATADA"))
            total += valor
            cur.execute(
                "INSERT INTO fato_despesa "
                "(sq_despesa, tp_prestacao, sq_candidato, cd_cargo, id_fornecedor, data, origem_despesa, "
                "descricao, tipo_documento, nr_documento, turno, dt_prestacao, valor, desatualizado) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,0)",
                (
                    (row.get("SQ_DESPESA") or NULO),
                    (row.get("TP_PRESTACAO_CONTAS") or NULO),
                    sq,
                    cd_cargo,
                    id_forn,
                    data,
                    (row.get("DS_ORIGEM_DESPESA") or NULO),
                    (row.get("DS_DESPESA") or NULO),
                    (row.get("DS_TIPO_DOCUMENTO") or NULO),
                    (row.get("NR_DOCUMENTO") or NULO),
                    NULO,
                    _data_iso(row.get("DT_PRESTACAO_CONTAS") or NULO),
                    valor,
                ),
            )

    cur.execute(
        "INSERT INTO carga (executada_em, dt_geracao_tse, arquivo, linhas_lidas, linhas_carga, total_declarado) "
        "VALUES (?,?,?,?,?,?)",
        (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            dt_geracao,
            csv_path.name,
            n_lidas,
            n_carga,
            round(total, 2),
        ),
    )
    conn.commit()

    # Agregados pre-computados por cargo (leitura rapida da API, sem scans de 1.7M linhas).
    cur.executescript(
        """
        CREATE TABLE resumo_candidato AS
        SELECT
            d.sq_candidato, d.nm_candidato, d.nr_candidato, d.sg_partido, d.nm_partido,
            d.nr_partido, d.cd_cargo, d.ds_cargo,
            COALESCE(MAX(f.desatualizado), 0) AS desatualizado,
            COUNT(f.id_despesa)             AS lancamentos,
            COALESCE(SUM(f.valor), 0.0)     AS total
        FROM dim_candidato d
        LEFT JOIN fato_despesa f ON f.sq_candidato = d.sq_candidato
        GROUP BY d.sq_candidato;

        CREATE TABLE resumo_cargo AS
        SELECT cd_cargo, MAX(ds_cargo) AS nome, COUNT(*) AS candidatos,
               SUM(lancamentos) AS lancamentos, SUM(total) AS total
        FROM resumo_candidato GROUP BY cd_cargo;

        CREATE TABLE resumo_partido_cargo AS
        SELECT cd_cargo, sg_partido, MAX(nm_partido) AS nome,
               SUM(lancamentos) AS lancamentos, SUM(total) AS total
        FROM resumo_candidato GROUP BY cd_cargo, sg_partido;

        CREATE TABLE resumo_origem_cargo AS
        SELECT cd_cargo, origem_despesa AS origem, COUNT(*) AS lancamentos, SUM(valor) AS total
        FROM fato_despesa WHERE origem_despesa IS NOT NULL
        GROUP BY cd_cargo, origem_despesa;

        CREATE TABLE resumo_mes_cargo AS
        SELECT cd_cargo, substr(data, 1, 7) AS mes, COUNT(*) AS lancamentos, SUM(valor) AS total
        FROM fato_despesa GROUP BY cd_cargo, mes;

        CREATE TABLE resumo_serie_cargo AS
        SELECT f.cd_cargo, f.data, d.sg_partido, SUM(f.valor) AS total
        FROM fato_despesa f JOIN dim_candidato d ON d.sq_candidato = f.sq_candidato
        GROUP BY f.cd_cargo, f.data, d.sg_partido;

        CREATE TABLE resumo_prestacao_candidato AS
        SELECT sq_candidato, tp_prestacao AS tipo, COUNT(*) AS lancamentos, SUM(valor) AS total
        FROM fato_despesa GROUP BY sq_candidato, tp_prestacao;

        CREATE INDEX IF NOT EXISTS idx_fato_cand   ON fato_despesa(sq_candidato);
        CREATE INDEX IF NOT EXISTS idx_fato_data   ON fato_despesa(data);
        CREATE INDEX IF NOT EXISTS idx_fato_cargo  ON fato_despesa(cd_cargo);
        CREATE INDEX IF NOT EXISTS idx_fato_cd_dat ON fato_despesa(cd_cargo, data);
        CREATE INDEX IF NOT EXISTS idx_fato_cd_ori ON fato_despesa(cd_cargo, origem_despesa);
        CREATE INDEX IF NOT EXISTS idx_fato_cd_sq  ON fato_despesa(cd_cargo, sq_candidato);
        CREATE INDEX IF NOT EXISTS idx_cand_cargo  ON dim_candidato(cd_cargo);
        CREATE INDEX IF NOT EXISTS idx_cand_part   ON dim_candidato(sg_partido);
        CREATE INDEX IF NOT EXISTS idx_rc_cargo    ON resumo_candidato(cd_cargo);
        CREATE INDEX IF NOT EXISTS idx_rc_part     ON resumo_candidato(sg_partido);
        CREATE INDEX IF NOT EXISTS idx_pc_cargo    ON resumo_partido_cargo(cd_cargo);
        CREATE INDEX IF NOT EXISTS idx_oc_cargo    ON resumo_origem_cargo(cd_cargo);
        CREATE INDEX IF NOT EXISTS idx_mc_cargo    ON resumo_mes_cargo(cd_cargo);
        CREATE INDEX IF NOT EXISTS idx_sc_cargo    ON resumo_serie_cargo(cd_cargo);
        CREATE INDEX IF NOT EXISTS idx_prc_cand    ON resumo_prestacao_candidato(sq_candidato);
        """
    )
    conn.commit()

    print(
        f"Linhas lidas: {n_lidas} | lancamentos na carga: {n_carga} | "
        f"candidatos: {len(candidatos_inseridos)} | total: {total:,.2f} | dt_geracao: {dt_geracao}"
    )

    db.aplicar_schema(conn)
    db.garantir_qc(conn)
    conn.close()
    print("Views recriadas e QC executado. Banco atualizado.")


def main() -> None:
    ap = argparse.ArgumentParser(description="ETL da prestacao de contas (despesas contratadas) para o banco")
    ap.add_argument("--csv", required=True, help="Caminho do CSV de despesas contratadas")
    ap.add_argument("--cargo", default="", help="CD_CARGO (1=Presidente, 3=Governador, 5=Senador, 6=Dep.Federal, 7=Dep.Estadual, 8=Dep.Distrital). Vazio = todos.")
    ap.add_argument("--dt-geracao", default="", help="Data de geracao (dd/mm/aaaa). Vazio usa a do arquivo.")
    args = ap.parse_args()
    reconstruir(Path(args.csv), args.cargo, args.dt_geracao)


if __name__ == "__main__":
    main()