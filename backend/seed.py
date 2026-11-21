"""Seed de candidatos desatualizados.

A fonte atual do TSE (despesas por documento, 21/11/2026) NAO traz o PT/Lula.
Para que ele apareca no painel, inserimos os numeros da carga parcial anterior
(12/09/2026) marcados como DESATUALIZADOS (desatualizado = 1). O painel mostra
um aviso claro de que esses valores nao correspondem a carga atual.

Os agregados abaixo vieram da carga de 12/09/2026 (arquivo
despesas_contratadas_candidatos_2026_BRASIL, CD_CARGO=1), por origem de despesa.
"""
from __future__ import annotations

import sqlite3

# sq, nm, nr, sg_partido, nm_partido, nr_partido
DESATUALIZADOS = [
    {
        "sq_candidato": "280002542548",
        "nm_candidato": "LUIZ INACIO LULA DA SILVA",
        "nr_candidato": "13",
        "sg_partido": "PT",
        "nm_partido": "PARTIDO DOS TRABALHADORES",
        "nr_partido": "13",
        "dt_geracao": "12/09/2026",
        "origens": [
            ("Serviços prestados por terceiros", 76, 8919595.36),
            ("Publicidade por adesivos", 75, 2833068.66),
            ("Publicidade por materiais impressos", 91, 2823480.48),
            ("Passagem Aérea", 194, 654926.16),
            ("Eventos de promoção da candidatura", 1, 231341.00),
            ("Taxa de Administração de Financiamento Coletivo", 3, 6299.48),
        ],
    }
]

AVISO = (
    "Os valores de {nome} ({partido}) sao da carga parcial de {dt} e estao "
    "DESATUALIZADOS: nao constam na fonte de despesas por documento de 21/11/2026."
)


def aplicar_seed(conn: sqlite3.Connection) -> list[dict]:
    cur = conn.cursor()
    avisos = []
    for c in DESATUALIZADOS:
        sq = c["sq_candidato"]
        # dim_candidato (nao duplica se ja existir)
        cur.execute(
            "INSERT OR IGNORE INTO dim_candidato "
            "(sq_candidato, nm_candidato, nr_candidato, sg_partido, nm_partido, nr_partido, desatualizado) "
            "VALUES (?,?,?,?,?,?,1)",
            (sq, c["nm_candidato"], c["nr_candidato"], c["sg_partido"], c["nm_partido"], c["nr_partido"]),
        )
        # garante a linha em dim_tempo para a data da carga antiga (FK)
        cur.execute(
            "INSERT OR IGNORE INTO dim_tempo (data, ano, mes, dia, semana) VALUES (?,?,?,?,?)",
            ("2026-09-12", 2026, 9, 12, 37),
        )
        # remove insercoes anteriores do seed (idempotente)
        cur.execute("DELETE FROM fato_despesa WHERE sq_candidato = ? AND desatualizado = 1", (sq,))
        for origem, lanc, valor in c["origens"]:
            base = round(valor / lanc, 2)
            for i in range(lanc):
                v = base if i < lanc - 1 else round(valor - base * (lanc - 1), 2)
                cur.execute(
                    "INSERT INTO fato_despesa "
                    "(sq_despesa, tp_prestacao, sq_candidato, id_fornecedor, data, origem_despesa, "
                    "descricao, tipo_documento, nr_documento, turno, dt_prestacao, valor, desatualizado) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1)",
                    (
                        f"SEED-{sq}-{i}",
                        "Parcial (12/09)",
                        sq,
                        None,
                        "2026-09-12",
                        origem,
                        "Sem fornecedor informado (seed)",
                        "Documento",
                        "SEED",
                        "",
                        "2026-09-12",
                        v,
                    ),
                )
        avisos.append(
            {
                "sq_candidato": sq,
                "nome": c["nm_candidato"],
                "partido": c["sg_partido"],
                "texto": AVISO.format(nome=c["nm_candidato"], partido=c["sg_partido"], dt=c["dt_geracao"]),
            }
        )
    conn.commit()
    return avisos


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import db

    conn = db.conectar()
    a = aplicar_seed(conn)
    conn.close()
    print(f"Seed aplicado: {len(a)} candidato(s) desatualizado(s)")
    for x in a:
        print("  -", x["texto"])