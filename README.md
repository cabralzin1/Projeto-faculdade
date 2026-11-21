# Projeto Faculdade
Painel com a **despesa contratada declarada** pelos candidatos, a partir dos
Dados Abertos do TSE. O painel **mede**, não opina: todos os candidatos recebem
o mesmo tratamento. Cobre **todos os cargos** (Presidente, Governador, Senador,
Deputado Federal, Estadual e Distrital) e tem uma visão geral de custos por
partido.

Disciplina de Projeto de Software do curso de analise e desenvolvimento de sistemas

> Metodologia completa (fonte, três achados da carga, pipeline, modelo, QC e
> limitações): [METODOLOGIA.md](METODOLOGIA.md).

## Integrantes

| Nome | RA |
| ---- | -- |
| _Guilherme Cabral de Oliveira_ | _2403377_ |

- Board do projeto: _https://app.clickup.com/90171389193/v/li/901715205335 
- rep do projeto: https://github.com/cabralzin1/Projeto-faculdade/
- Vídeo da Sprint 1: _https://youtu.be/O573eEB9m1I_

## Como executar

O painel agora depende de uma **API REST** (FastAPI) que lê o banco dimensional
`Dados/campanha.db`. Toda a apuração é feita a partir do banco — não há mais JSON
estático embutido.

> **O banco `Dados/campanha.db` não é versionado no Git** (tem ~670 MB, acima do
> limite de 100 MB por arquivo do GitHub). Em um clone novo, gere-o uma vez com o
> ETL (seção "Atualizar a carga" abaixo); a pasta `Dados/` é criada
> automaticamente. O arquivo-fonte do TSE fica fora do repositório.

Pré-requisitos: **Python 3.12**. Na primeira execução o script cria o ambiente
virtual (`.venv`) e instala as dependências (`backend/requirements.txt`).

```bash
# Windows (cria .venv + instala dependências + sobe a API na porta 8000)
iniciar.bat

# Linux/macOS
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Depois abra **http://127.0.0.1:8000** no navegador. A API serve o próprio painel
(o `index.html`) e responde em `/api/*`.

> Abrir o `index.html` por `file://` ainda funciona (detecção automática: nesse
> caso o front aponta para `http://127.0.0.1:8000/api`, com CORS habilitado), mas
> a forma recomendada é via servidor acima.

Testado em Chrome, Edge e Brave.

### Atualizar a carga (contas finais pós-pleito)

A fonte atual é o dataset de **prestação de contas por candidato** do TSE
(`despesas_contratadas_candidatos_2026_BRASIL.csv`). Por padrão o ETL ingere
**todos os cargos**; use `--cargo` para restringir a um cargo (1=Presidente,
3=Governador, 5=Senador, 6=Dep. Federal, 7=Dep. Estadual, 8=Dep. Distrital):

```bash
python backend/etl.py --csv "../prestacao_de_contas_eleitorais_candidatos_2026/despesas_contratadas_candidatos_2026_BRASIL.csv"
# opcional: --cargo 1 --dt-geracao 21/11/2026
```

O ETL recria as dimensões e a fato, grava a tabela `carga`, pré-computa os
agregados por cargo (`resumo_*`) e roda as views + o controle de qualidade
automaticamente.

## API REST

| Método | Rota | Descrição |
| ------ | ---- | --------- |
| GET | `/api/carga?cargo=1` | Carga completa do cargo (resumo, candidatos, série diária, origens e partidos). `cargo` = `CD_CARGO` (padrão 1). |
| GET | `/api/candidatos?cargo=1` | Listagem **recalculada no banco**. Filtros: `cargo`, `data_ini`, `data_fim` (AAAA-MM-DD) e `categoria` (origem da despesa). |
| GET | `/api/candidatos/{sq}` | Detalhe de um candidato por origem e por tipo de prestação. |
| GET | `/api/filtros?cargo=1` | Opções dos filtros: partidos, prestações, categorias e período disponível. |
| GET | `/api/cargos` | Lista de cargos com totais agregados (candidatos, lançamentos, total). |
| GET | `/api/partidos` | Custos por partido. Sem `cargo`, soma **todos os cargos** (visão geral). |
| GET | `/api/qc` | Relatório de controle de qualidade (contagem de registros e soma por origem). |

## Arquitetura

```
.
├── index.html              estrutura da página (painel)
├── CSS/page.css            estilos
├── JS/
│   ├── data.js             camada de dados: fetch() contra a API (substituiu o JSON estático)
│   └── site.js             apresentação: filtros, ordenação, comparação, gráficos
├── Dados/campanha.db       banco dimensional (SQLite) — fonte de verdade
└── backend/
    ├── main.py             API FastAPI (endpoints /api/*) + serve o painel
    ├── db.py               conexão, aplicação das views e controle de qualidade
    ├── schema.sql          views de apoio ao painel
    ├── etl.py              ETL CSV do TSE -> banco (atualização da carga)
    └── requirements.txt    dependências (fastapi, uvicorn)
```

Modelo dimensional: `fato_despesa` (com `cd_cargo`) ligada às dimensões
`dim_candidato`, `dim_fornecedor` e `dim_tempo`, mais a tabela `carga` (metadados
da importação) e as tabelas `resumo_*` (agregados por cargo pré-computados no ETL
para leitura rápida da API).

## Funcionalidades por sprint

### Sprint 1 — Front-end (entrega 14/09)

- [x] primeira visão: despesa declarada por candidato (valor + lançamentos)
- [x] resumo da carga: total, quantidade de candidatos, lançamentos e data de geração do TSE
- [x] prestação parcial visível junto dos números
- [x] busca, filtro por partido e por tipo de prestação, ordenação
- [x] comparação entre dois candidatos com o mesmo critério, com validação no front (não aparece o mesmo candidato duas vezes)
- [x] metodologia dos três achados da carga (BRASIL, SQ_DESPESA, tipos de prestação) — ver [METODOLOGIA.md](METODOLOGIA.md)

### Sprint 2 — Back-end (entrega 13/10)

- [x] API REST com listagem de candidatos e detalhe por origem (`/api/candidatos`, `/api/candidatos/{sq}`)
- [x] Substituição de `data.js` por `fetch()` nas funções de `Dados`
- [x] Recálculo a partir do banco, sem o JSON estático (`/api/candidatos` agrega direto da `fato_despesa`)

### Sprint 3 — Banco de dados (entrega 08/11)

- [x] Modelo dimensional (`fato_despesa` + `dim_candidato`/`dim_fornecedor`/`dim_tempo` + `carga`)
- [x] Persistência em SQLite e views de apoio ao painel (`backend/schema.sql`: `vw_candidato_total`, `vw_origem_total`, `vw_partido_total`, `vw_serie_diaria`, etc.)
- [x] Controle de qualidade: contagem de registros e soma por origem (`backend/db.py` → tabela `qc_resultado`, endpoint `/api/qc`)

### Entrega final — Painel integrado (22/11)

- [x] Filtro por período e categoria alimentado pelo banco (filtros "De/Até" e "Categoria" no topo; agregação recalculada em `/api/candidatos`)
- [x] Painel por cargo (seletor "Cargo") para todos os cargos + visão geral de custos por partido (`/api/cargos`, `/api/partidos`)
- [x] Atualização da carga com as contas finais pós-pleito (caminho via `backend/etl.py`; ver seção "Atualizar a carga")
- [x] Documentação de metodologia e limitações (seção abaixo e [METODOLOGIA.md](METODOLOGIA.md))

## O que os números representam

Despesa contratada declarada até a data da carga (`DT_GERACAO` do arquivo TSE).
Não é o gasto total da campanha. Recorte: **todos os cargos** (`CD_CARGO`) no
arquivo de despesas contratadas por candidato do consolidado BRASIL.

## Metodologia

- **Fonte única:** Portal de Dados Abertos do TSE — Prestação de Contas Eleitorais
  2026, **despesas contratadas por candidato**, arquivo consolidado `BRASIL`
  (`despesas_contratadas_candidatos_2026_BRASIL.csv`), **todos os cargos**.
- **Unidade de análise:** cada linha do arquivo é um **lançamento** de despesa
  contratada declarada (`fato_despesa`). O valor somado (`VR_DESPESA_CONTRATADA`) é a
  despesa declarada.
- **Dimensões:** candidato (com cargo), fornecedor e tempo. A data usada para
  série/período é a data da despesa (`DT_DESPESA`); o momento da carga é
  `DT_GERACAO`.
- **Cálculo:** os agregados por cargo (candidato, partido, origem/categoria, mês e
  série diária) são pré-computados no ETL em tabelas `resumo_*` e expostos pela API,
  garantindo leitura rápida mesmo para cargos com milhares de candidatos.
- **Controle de qualidade (`/api/qc`):** confere (a) contagem de lançamentos na
  `fato_despesa` contra `carga.linhas_carga`; (b) soma total da `fato_despesa`
  contra `carga.total_declarado`; (c) soma por origem (`vw_origem_total`) contra a
  soma da fato; (d) nº de candidatos distintos na fato == linhas em `dim_candidato`.
- **Imparcialidade:** todos os candidatos recebem o mesmo tratamento — mesmos
  filtros, mesmo recorte e mesmos critérios de apuração. O painel mede, não opina.

### Números da carga atual (21/11/2026 — prestação final)

- **Todos os cargos:** **R$ 6.699.677.258,91** · **1.793.596** lançamentos ·
  **19.687** candidatos.
- Por cargo: Presidente R$ 286,9 mi (14) · Governador R$ 644,5 mi (197) · Senador
  R$ 532,5 mi (316) · Deputado Federal R$ 3,41 bi (7.652) · Deputado Estadual
  R$ 1,78 bi (11.081) · Deputado Distrital R$ 46,9 mi (427).
- Por partido (todos os cargos, top 3): **PL** R$ 1,21 bi · **PT** R$ 741,3 mi ·
  **PSD** R$ 665,2 mi.
- A carga inclui prestações **Final** e **Parcial** (`TP_PRESTACAO_CONTAS`); valores
  de candidatos ainda em prestação parcial tendem a crescer.

## Limitações

- **Despesa contratada ≠ gasto total.** É o que foi declarado até a data da carga;
  não inclui arrecadação, sobras, nem despesas ainda não lançadas.
- **Prestação parcial.** A geração de 21/11/2026 ainda contém prestações **parciais**
  de alguns candidatos (`TP_PRESTACAO_CONTAS = "Parcial"`); os totais podem crescer.
- **Qualidade dos dados de origem.** Nomes de origem/categoria (`DS_ORIGEM_DESPESA`) e
  fornecedores seguem o que o TSE publicou; há campos `#NULO` (não informados) e
  categorias semelhantes que não são unificadas.
- **Escopo do recorte.** Todos os cargos do consolidado BRASIL (Presidente,
  Governador, Senador, Deputado Federal, Estadual e Distrital); não cobre estados
  individualmente nem despesas de diretório partidário.
