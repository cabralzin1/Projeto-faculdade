# Metodologia

Documento de metodologia do painel de **despesa contratada declarada** dos
candidatos nas eleições de 2026. Explica a fonte, os três achados da carga, o
pipeline de dados, o modelo dimensional, os controles de qualidade e as
limitações.

## 1. Fonte e recorte

- **Fonte:** Portal de Dados Abertos do TSE — Prestação de Contas Eleitorais
  2026, **despesas contratadas por candidato**, arquivo consolidado
  `despesas_contratadas_candidatos_2026_BRASIL.csv` (53 colunas).
- **Data da carga:** `DT_GERACAO = 21/11/2026` (contas finais pós-pleito).
- **Recorte:** **todos os cargos** (`CD_CARGO`): Presidente, Governador, Senador,
  Deputado Federal, Deputado Estadual e Deputado Distrital.
- **Unidade de análise:** cada linha do arquivo é um **lançamento** de despesa
  contratada declarada. O valor somado (`VR_DESPESA_CONTRATADA`) é a despesa
  declarada.

### Números da carga (21/11/2026)

| Cargo | `CD_CARGO` | Candidatos | Lançamentos | Total declarado |
| ----- | ---------- | ---------: | ----------: | --------------: |
| Presidente | 1 | 14 | 4.693 | R$ 286.940.045,58 |
| Governador | 3 | 197 | 77.027 | R$ 644.476.060,34 |
| Senador | 5 | 316 | 75.283 | R$ 532.488.163,19 |
| Deputado Federal | 6 | 7.652 | 931.385 | R$ 3.405.794.605,89 |
| Deputado Estadual | 7 | 11.081 | 681.510 | R$ 1.783.108.046,42 |
| Deputado Distrital | 8 | 427 | 23.698 | R$ 46.870.337,49 |
| **Todos** | — | **19.687** | **1.793.596** | **R$ 6.699.677.258,91** |

## 2. Os três achados da carga

### 2.1 Achado 1 — Usar o consolidado BRASIL (não arquivos por UF)

O TSE publica a prestação de contas em dois recortes: por Unidade Federativa e
consolidado **BRASIL**. O painel usa o **consolidado BRASIL**
(`..._BRASIL.csv`), que já reúne todos os estados e todos os cargos em um único
arquivo.

Motivos:

- **Evita fragmentação:** não é preciso baixar e unir 27 arquivos estaduais.
- **Evita duplicidade:** o consolidado já é a soma dos estados; somar arquivos
  por UF + consolidado duplicaria os valores.
- **Cobre todos os cargos** de uma vez, permitindo o seletor "Cargo" e a visão
  geral por partido.

O recorte por cargo é feito por `CD_CARGO` (1, 3, 5, 6, 7, 8), e não por UF.

### 2.2 Achado 2 — `SQ_DESPESA` não é único por linha

`SQ_DESPESA` identifica a despesa, mas **não é uma chave única por linha**:

- Linhas na carga: **1.793.596**
- `SQ_DESPESA` distintos: **1.448.491**
- Linhas que compartilham `SQ_DESPESA` com outra linha: **345.105** (~19%)
- `SQ_DESPESA = -1` (não informado): **3.172** ocorrências (1 por candidato)

Exemplos de `SQ_DESPESA` repetido: um mesmo identificador aparece centenas de
vezes para o **mesmo candidato no mesmo dia** (ex.: `82124758` → 380 linhas).

**Consequência metodológica:** o painel **não deduplica por `SQ_DESPESA`**. Cada
linha é tratada como um lançamento. Se deduplicássemos por `SQ_DESPESA`,
perderíamos ~19% dos lançamentos (e parte do valor). O `SQ_DESPESA` é guardado
como atributo informativo, não como chave.

### 2.3 Achado 3 — Tipos de prestação (`TP_PRESTACAO_CONTAS`)

A carga mistura três tipos de prestação:

| `TP_PRESTACAO_CONTAS` | Linhas | Candidatos | Total |
| --------------------- | -----: | ---------: | ----: |
| Final | 1.792.069 | 19.440 | R$ 6.694.386.517,73 |
| Relatório Financeiro | 836 | 78 | R$ 2.848.571,13 |
| Parcial | 691 | 169 | R$ 2.442.170,05 |

**Consequência metodológica:**

- O painel **inclui todos os tipos** e mostra o(s) tipo(s) de cada candidato
  (linha "nº X · PARTIDO · Final, Parcial").
- Valores de candidatos com prestação **Parcial** tendem a crescer; o painel
  registra isso como ressalva.
- "Relatório Financeiro" e "Parcial" são minoria (poucas linhas), mas foram
  mantidos para não distorcer o total declarado.

## 3. Pipeline de dados

```
CSV do TSE (BRASIL)
      │  backend/etl.py
      ▼
Banco dimensional SQLite (Dados/campanha.db)
      │  backend/db.py (views + QC)
      ▼
API REST FastAPI (backend/main.py)  →  /api/*
      │  fetch()
      ▼
Painel (index.html + JS/data.js + JS/site.js + CSS/page.css)
```

### 3.1 ETL (`backend/etl.py`)

- Detecta encoding (utf-8-sig/latin-1/cp1252) e separador (`;`, `,`, `\t`).
- Converte `VR_DESPESA_CONTRATADA` do formato BR (`1.234,56`) para número.
- Converte `DT_DESPESA` (dd/mm/aaaa) para ISO (`aaaa-mm-dd`); se vazia, usa
  `DT_PRESTACAO_CONTAS`.
- Popula as dimensões `dim_candidato` (com `cd_cargo`/`ds_cargo`),
  `dim_fornecedor` e `dim_tempo`, e a fato `fato_despesa` (com `cd_cargo`).
- Pré-computa os agregados por cargo nas tabelas `resumo_*` (ver seção 5).
- Grava a tabela `carga` (metadados) e executa as views + o QC.

### 3.2 API (`backend/main.py`)

- `/api/carga?cargo=1` — resumo, candidatos, série diária (por partido),
  origens e partidos do cargo.
- `/api/candidatos?cargo=1` — listagem recalculada (filtros `data_ini`,
  `data_fim`, `categoria`).
- `/api/candidatos/{sq}` — detalhe por origem e por tipo de prestação.
- `/api/filtros?cargo=1` — opções dos filtros.
- `/api/cargos` — cargos com totais agregados.
- `/api/partidos` — custos por partido (sem `cargo`, soma todos os cargos).
- `/api/qc` — relatório de controle de qualidade.

### 3.3 Frontend

- `JS/data.js` concentra o `fetch()` (sem JSON estático).
- `JS/site.js` renderiza filtros, gráficos (Chart.js), lista, comparação e a
  visão geral por partido.
- O seletor "Cargo" recarrega o painel com `?cargo=N`.

## 4. Modelo dimensional

- **Fato:** `fato_despesa` (uma linha por lançamento; `valor` = despesa
  contratada).
- **Dimensões:** `dim_candidato` (com cargo e partido), `dim_fornecedor`,
  `dim_tempo`.
- **Metadados:** `carga` (arquivo, data de geração, linhas lidas, total).
- **Agregados:** `resumo_candidato`, `resumo_cargo`, `resumo_partido_cargo`,
  `resumo_origem_cargo`, `resumo_mes_cargo`, `resumo_serie_cargo`,
  `resumo_prestacao_candidato`.

Índices de apoio: `fato_despesa(cd_cargo)`, `(cd_cargo, data)`,
`(cd_cargo, origem_despesa)`, `(cd_cargo, sq_candidato)`, `dim_candidato(cd_cargo)`
e índices nas tabelas `resumo_*`.

## 5. Agregados pré-computados e performance

As consultas da API leem as tabelas `resumo_*` (pequenas) em vez de varrer
`fato_despesa` (1,79 mi de linhas) a cada request. Tempos medidos (local):

| Cargo | `/api/carga` |
| ----- | ------------ |
| Presidente | ~0,12 s |
| Governador | ~0,27 s |
| Deputado Federal (7.652) | ~0,70 s |
| Deputado Estadual (11.081) | ~0,94 s |

## 6. Controle de qualidade (`backend/db.py` → `/api/qc`)

O QC grava o resultado na tabela `qc_resultado` e confere:

1. Lançamentos atuais (sem desatualizados) == `carga.linhas_carga`.
2. Soma atual == `carga.total_declarado`.
3. Soma por origem (`vw_origem_total`) == soma total de `fato_despesa`.
4. Nº de candidatos distintos na fato == linhas em `dim_candidato`.
5. Candidatos desatualizados (seed) — apenas informativo.

Resultado atual: **todos `[OK]`**.

## 7. Escolhas de modelagem

- **Janela temporal:** a fonte contém lançamentos com datas claramente erradas
  (2025 e 2027/2028). O período exposto e a série diária são limitados a **2026**
  (`2026-01-01` a `2026-12-31`).
- **Início do gráfico de evolução:** `06/08/2026` (período de campanha), com
  remoção de dias iniciais/finais sem valor.
- **Carga por candidato:** as origens detalhadas vão no payload apenas para cargos
  pequenos (até 500 candidatos); nos grandes, são carregadas sob demanda
  (`/api/candidatos/{sq}`).
- **Desempenho:** agregados por cargo em `resumo_*` (ver seção 5).

## 8. Limitações

- **Despesa contratada ≠ gasto total.** É o que foi declarado até a data da
  carga; não inclui arrecadação, sobras, nem despesas ainda não lançadas.
- **Prestação parcial.** A geração de 21/11/2026 ainda contém prestações
  parciais de alguns candidatos; os totais podem crescer.
- **Qualidade dos dados de origem.** Nomes de origem/categoria
  (`DS_ORIGEM_DESPESA`) e fornecedores seguem o que o TSE publicou; há campos
  `#NULO` e categorias semelhantes que não são unificadas.
- **Escopo.** Todos os cargos do consolidado BRASIL; não cobre estados
  individualmente nem despesas de diretório partidário.
- **`SQ_DESPESA` não é chave única** (ver 2.2); cada linha é um lançamento.

## 9. Reprodutibilidade

```bash
# 1) Reconstruir o banco (todos os cargos)
python backend/etl.py --csv "../prestacao_de_contas_eleitorais_candidatos_2026/despesas_contratadas_candidatos_2026_BRASIL.csv"

# 2) Rodar o QC
python backend/db.py

# 3) Subir a API + painel
uvicorn backend.main:app --host 127.0.0.1 --port 8000
# abra http://127.0.0.1:8000
```

## 10. Referências

- TSE — Dados Abertos, Prestação de Contas Eleitorais 2026:
  <https://dadosabertos.tse.jus.br/dataset/prestacao-de-contas-eleitorais-2026>
- Arquivo-fonte: `despesas_contratadas_candidatos_2026_BRASIL.csv`
  (`DT_GERACAO = 21/11/2026`).