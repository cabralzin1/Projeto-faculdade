# Diagramas do Projeto

Diagramas do painel de despesas contratadas 2026. Cada seção tem a fonte
**Mermaid** (editável, renderiza no GitHub) e o SVG/PNG correspondente na pasta
[`diagramas/`](diagramas/).

- [MER (Entidade-Relacionamento)](diagramas/mer.svg) · [PNG](diagramas/mer.png)
- [Casos de Uso](diagramas/casos_de_uso.svg) · [PNG](diagramas/casos_de_uso.png)
- [Classes](diagramas/classes.svg) · [PNG](diagramas/classes.png)

## 1. MER — Modelo Entidade-Relacionamento

Modelo dimensional: uma tabela fato (`fato_despesa`) ligada às dimensões
`dim_candidato`, `dim_fornecedor` e `dim_tempo`, mais a tabela `carga` (metadados
da importação) e as tabelas `resumo_*` (agregados pré-computados).

```mermaid
erDiagram
    dim_candidato ||--o{ fato_despesa : "sq_candidato"
    dim_fornecedor ||--o{ fato_despesa : "id_fornecedor"
    dim_tempo ||--o{ fato_despesa : "data"
    carga ||--o{ fato_despesa : "registra"

    dim_candidato {
        text sq_candidato PK
        text nm_candidato
        text nr_candidato
        text sg_partido
        text nm_partido
        text nr_partido
        text cd_cargo
        text ds_cargo
        int desatualizado
    }
    dim_fornecedor {
        int id_fornecedor PK
        text cpf_cnpj UK
        text nm_fornecedor
        text nm_receita_federal
        text tipo
        text cnae
        text uf
        text municipio
    }
    dim_tempo {
        text data PK
        int ano
        int mes
        int dia
        int semana
    }
    fato_despesa {
        int id_despesa PK
        text sq_despesa
        text tp_prestacao
        text sq_candidato FK
        text cd_cargo
        int id_fornecedor FK
        text data FK
        text origem_despesa
        text descricao
        text tipo_documento
        text nr_documento
        text turno
        text dt_prestacao
        float valor
        int desatualizado
    }
    carga {
        text executada_em
        text dt_geracao_tse
        text arquivo
        int linhas_lidas
        int linhas_carga
        float total_declarado
    }
```

**Agregados (`resumo_*`)** — derivados de `fato_despesa`/`dim_candidato`:
`resumo_candidato`, `resumo_cargo`, `resumo_partido_cargo`,
`resumo_origem_cargo`, `resumo_mes_cargo`, `resumo_serie_cargo`,
`resumo_prestacao_candidato`.

## 2. Casos de Uso

Atores: **Usuário** (Professor/Pesquisador), **Administrador** e **TSE** (fonte
de dados). O usuário visualiza o painel; filtros, busca, comparação e detalhes
estendem o caso principal. O administrador atualiza a carga (ETL), que inclui a
execução do QC. O TSE fornece o CSV.

```mermaid
flowchart LR
    U["Usuário<br/>(Professor/Pesquisador)"]
    A["Administrador"]
    T["TSE<br/>(fonte de dados)"]

    subgraph Sistema["Painel de Despesas Contratadas 2026"]
        P(("Visualizar painel"))
        C1(("Filtrar por cargo"))
        C2(("Filtrar por período"))
        C3(("Filtrar por categoria"))
        C4(("Buscar e ordenar"))
        C5(("Comparar candidatos"))
        C6(("Ver evolução por partido"))
        C7(("Ver visão geral por partido"))
        C8(("Consultar detalhes"))
        E(("Atualizar carga (ETL)"))
        Q(("Executar QC"))
    end

    U --> P
    U -.-> C1
    U -.-> C2
    U -.-> C3
    U -.-> C4
    U -.-> C5
    U -.-> C6
    U -.-> C7
    U -.-> C8
    A --> E
    A --> Q
    T -.->|"fornece CSV"| E
    E -.->|<<include>>| Q
```

## 3. Diagrama de Classes

Camadas: **front** (`Dados`, `SiteController`), **API** (`API`), **banco**
(`DB`, `ETL`) e **domínio** (`Candidato`, `Despesa`).

```mermaid
classDiagram
    class Dados {
        +CARGA
        +BASE
        +CARGO
        +CARGOS
        +init(cargo)
        +obterCarga()
        +listarCandidatos()
        +filtrarPorBanco()
        +detalheCandidato(sq)
        +listarCargos()
        +partidos(cargo)
    }
    class SiteController {
        +estado
        +graficos
        +iniciar()
        +atualizarGraficos()
        +desenharLista()
        +desenharComparacao()
        +desenharPartidos()
        +popularCargos()
    }
    class API {
        +app
        +carga()
        +candidatos()
        +candidato()
        +filtros()
        +cargos()
        +partidos()
        +qc()
    }
    class DB {
        +DB_PATH
        +SCHEMA_PATH
        +conectar(create)
        +aplicar_schema(conn)
        +garantir_qc(conn)
    }
    class ETL {
        +RAIZ
        +NULO
        +reconstruir(csv, cargo, dt)
        +_detectar(path)
        +_num(br)
    }
    class Candidato {
        +sq_candidato
        +nm_candidato
        +nr_candidato
        +sg_partido
        +cd_cargo
        +total
        +lancamentos
        +origens
        +prestacoes
    }
    class Despesa {
        +id_despesa
        +sq_despesa
        +tp_prestacao
        +sq_candidato
        +cd_cargo
        +id_fornecedor
        +data
        +origem_despesa
        +valor
    }
    SiteController --> Dados : usa
    Dados --> API : HTTP fetch
    API --> DB : usa
    ETL --> DB : escreve
    API --> Candidato : retorna
    API --> Despesa : retorna
```