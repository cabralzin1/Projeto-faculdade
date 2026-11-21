-- Views de apoio ao painel (Sprint 3).
-- Modelo dimensional: fato_despesa + dim_candidato/dim_fornecedor/dim_tempo + carga.
-- Todas as views sao idempotentes (CREATE VIEW IF NOT EXISTS) e podem ser recriadas
-- a cada carga, pois dependem apenas das tabelas base.

CREATE VIEW IF NOT EXISTS vw_candidato_total AS
SELECT
    d.sq_candidato,
    d.nm_candidato,
    d.nr_candidato,
    d.sg_partido,
    d.nm_partido,
    d.nr_partido,
    d.cd_cargo,
    d.ds_cargo,
    COALESCE(MAX(f.desatualizado), 0) AS desatualizado,
    COUNT(f.id_despesa)              AS lancamentos,
    COALESCE(SUM(f.valor), 0.0)      AS total
FROM dim_candidato d
LEFT JOIN fato_despesa f ON f.sq_candidato = d.sq_candidato
GROUP BY d.sq_candidato;

CREATE VIEW IF NOT EXISTS vw_cargo_total AS
SELECT
    d.cd_cargo                        AS cd_cargo,
    MAX(d.ds_cargo)                   AS nome,
    COUNT(DISTINCT d.sq_candidato)    AS candidatos,
    COUNT(f.id_despesa)               AS lancamentos,
    COALESCE(SUM(f.valor), 0.0)       AS total
FROM dim_candidato d
LEFT JOIN fato_despesa f ON f.sq_candidato = d.sq_candidato
GROUP BY d.cd_cargo;

CREATE VIEW IF NOT EXISTS vw_partido_total AS
SELECT
    d.sg_partido,
    MAX(d.nm_partido)               AS nome,
    COUNT(f.id_despesa)             AS lancamentos,
    COALESCE(SUM(f.valor), 0.0)     AS total
FROM fato_despesa f
JOIN dim_candidato d ON d.sq_candidato = f.sq_candidato
GROUP BY d.sg_partido;

CREATE VIEW IF NOT EXISTS vw_partido_cargo_total AS
SELECT
    d.cd_cargo                      AS cd_cargo,
    d.sg_partido                    AS sg_partido,
    MAX(d.nm_partido)               AS nome,
    COUNT(f.id_despesa)             AS lancamentos,
    COALESCE(SUM(f.valor), 0.0)     AS total
FROM fato_despesa f
JOIN dim_candidato d ON d.sq_candidato = f.sq_candidato
GROUP BY d.cd_cargo, d.sg_partido;

CREATE VIEW IF NOT EXISTS vw_origem_total AS
SELECT
    origem_despesa                  AS origem,
    COUNT(*)                        AS lancamentos,
    COALESCE(SUM(valor), 0.0)       AS total
FROM fato_despesa
GROUP BY origem_despesa;

CREATE VIEW IF NOT EXISTS vw_candidato_origem AS
SELECT
    sq_candidato,
    origem_despesa                  AS origem,
    COUNT(*)                        AS lancamentos,
    COALESCE(SUM(valor), 0.0)       AS total
FROM fato_despesa
GROUP BY sq_candidato, origem_despesa;

CREATE VIEW IF NOT EXISTS vw_candidato_prestacao AS
SELECT
    sq_candidato,
    tp_prestacao                    AS tipo,
    COUNT(*)                        AS lancamentos,
    COALESCE(SUM(valor), 0.0)       AS total
FROM fato_despesa
GROUP BY sq_candidato, tp_prestacao;

CREATE VIEW IF NOT EXISTS vw_prestacao_total AS
SELECT
    tp_prestacao                    AS tipo,
    COUNT(*)                        AS lancamentos,
    COALESCE(SUM(valor), 0.0)       AS total
FROM fato_despesa
GROUP BY tp_prestacao;

CREATE VIEW IF NOT EXISTS vw_serie_diaria AS
SELECT
    data,
    COUNT(*)                        AS lancamentos,
    COALESCE(SUM(valor), 0.0)       AS total
FROM fato_despesa
GROUP BY data
ORDER BY data;

CREATE VIEW IF NOT EXISTS vw_mes_total AS
SELECT
    substr(data, 1, 7)              AS mes,
    COUNT(*)                        AS lancamentos,
    COALESCE(SUM(valor), 0.0)       AS total
FROM fato_despesa
GROUP BY substr(data, 1, 7)
ORDER BY mes;