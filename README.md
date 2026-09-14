# Projeto Faculdade
Painel com a **despesa contratada declarada** pelos candidatos à Presidência,
a partir dos Dados Abertos do TSE. O painel **mede**, não opina: todos os
candidatos recebem o mesmo tratamento.

Disciplina de Projeto de Software do curso de analise e desenvolvimento de sistemas

## Integrantes

| Nome | RA |
| ---- | -- |
| _Guilherme Cabral de Oliveira_ | _2403377_ |

- Board do projeto: _https://app.clickup.com/90171389193/v/li/901715205335 
- rep do projeto: https://github.com/cabralzin1/Projeto-faculdade/
- Vídeo da Sprint 1: _https://youtu.be/O573eEB9m1I_

## Como executar front

Não há dependências, build ou instalação. Abra `painel/index.html` no navegador:

```bash
start index.html
```

Testado em Chrome, Edge e no Brave.

## Arquitetura

```
painel/
├── index.html          estrutura da página
├── css/page.css       estilos
├── js/
│   ├── data.js         camada de dados (carga TSE)
│   └── site.js          camada de apresentação: filtros, ordenação, comparação, validação
```

## Funcionalidades por sprint

### Sprint 1 — Front-end (entrega 14/09)

- [x] primeira visão: despesa declarada por candidato (valor + lançamentos)
- [x] resumo da carga: total, quantidade de candidatos, lançamentos e data de geração do TSE
- [x] prestação parcial visível junto dos números
- [x] busca, filtro por partido e por tipo de prestação, ordenação
- [x] comparação entre dois candidatos com o mesmo critério, com validação no front (nao aparecer o candidato x duas vezes - in process)
- [x] metodologia dos três achados da carga (BRASIL, SQ_DESPESA, tipos de prestação)

### Sprint 2 — Back-end (entrega 13/10)

- [ ] API REST com listagem de candidatos e detalhe por origem
- [ ] Substituição de `data.js` por `fetch()` nas funções de `Dados`
- [ ] Recálculo a partir do banco, sem o JSON estático

### Sprint 3 — Banco de dados (entrega 08/11)

- [ ] Modelo dimensional 
- [ ] Persistência em SQLite e views de apoio ao painel
- [ ] Controle de qualidade: contagem de registros e soma por origem

### Entrega final — Painel integrado (22/11)

- [ ] Filtro por período e categoria alimentado pelo banco
- [ ] Atualização da carga com as contas finais pós-pleito
- [ ] Documentação de metodologia e limitações

## O que os números representam

Despesa contratada declarada até a data da carga (`DT_GERACAO` do arquivo TSE).
Não é o gasto total da campanha. Recorte: `CD_CARGO = 1` no consolidado BRASIL.
