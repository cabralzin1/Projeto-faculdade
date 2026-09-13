# Projeto Faculdade
Sistema web para abertura e acompanhamento de requisições de compra internas.
Um colaborador registra o que precisa comprar, informa centro de custo e justificativa,
e a requisição entra na fila de aprovação do responsável.

Projeto da disciplina de Projeto de Software.

## Integrantes

| Nome | RA |
| ---- | -- |
| _Guilherme Cabral de Oliveira_ | _2403377_ |

- Board do projeto: _https://app.clickup.com/90171389193/v/li/901715205335 
- Vídeo da Sprint 1: _(colar link do YouTube ou Drive)_
- rep do projeto: https://github.com/cabralzin1/Projeto-faculdade/

## Como executar (Sprint 1) teste

Não há dependências, build ou instalação. Abra `painel/index.html` no navegador:

```bash
cd painel
start index.html
```

Testado em Chrome, Edge e no Brave.

## Arquitetura

```
painel/
├── index.html          estrutura da página
├── css/style.css       estilos
├── js/
│   ├── data.js         camada de dados (carga TSE, na Sprint 2 vira API)
│   └── app.js          camada de apresentação: filtros, ordenação, comparação, validação
```

## Funcionalidades por sprint

### Sprint 1 — Front-end (entrega 14/09)

- [x] Primeira visão: despesa declarada por candidato (valor + lançamentos)
- [x] Resumo da carga: total, quantidade de candidatos, lançamentos e data de geração do TSE
- [x] Ressalva de prestação parcial visível junto dos números
- [x] Busca, filtro por partido e por tipo de prestação, ordenação
- [x] Expansão das origens de despesa de cada candidato
- [x] Comparação entre dois candidatos com o mesmo critério, com validação no front
- [x] Metodologia dos três achados da carga (BRASIL, SQ_DESPESA, tipos de prestação)

### Sprint 2 — Back-end (entrega 13/10)

- [ ] API REST com listagem de candidatos e detalhe por origem
- [ ] Substituição de `data.js` por `fetch()` nas funções de `Dados`
- [ ] Recálculo a partir do banco, sem o JSON estático

### Sprint 3 — Banco de dados (entrega 08/11)

- [ ] Modelo dimensional já esboçado em `dados/02_carregar.py`
- [ ] Persistência em SQLite e views de apoio ao painel
- [ ] Controle de qualidade: contagem de registros e soma por origem

### Entrega final — Painel integrado (22/11)

- [ ] Filtro por período e categoria alimentado pelo banco
- [ ] Atualização da carga com as contas finais pós-pleito
- [ ] Documentação de metodologia e limitações

## O que os números representam

Despesa contratada declarada até a data da carga (`DT_GERACAO` do arquivo TSE).
Não é o gasto total da campanha. Recorte: `CD_CARGO = 1` no consolidado BRASIL.