# Roteiros de Vídeo — Sprint 2, Sprint 3 e Entrega Final

Duração ideal: **2 a 3 minutos por vídeo**. Estrutura padrão de cada roteiro:

1. **Abertura** (10–15 s) — quem é você e o que é a sprint.
2. **Board** (20–30 s) — mostrar as tarefas no ClickUp.
3. **Código** (40–60 s) — mostrar os arquivos principais.
4. **Funcionalidade nova** (40–60 s) — mostrar o painel funcionando.
5. **Fechamento** (10 s) — o que vem na próxima etapa.

> Troque `[seu nome]` pelo seu nome. Se algo não der para mostrar ao vivo (ex.:
> ETL demorado), mostre o resultado já executado.

---

## Vídeo 1 — Sprint 2: Back-end (entrega 13/10)

**Objetivo:** mostrar a API REST e a troca do JSON estático por `fetch()`.

**Roteiro:**

1. **Abertura**
   > "Olá, sou [seu nome]. Este é o vídeo da Sprint 2, a entrega do back-end do
   > painel de despesas contratadas de 2026. O objetivo foi criar a API REST e
   > fazer o front consumir os dados dela, em vez de um JSON estático."

2. **Board (ClickUp)**
   > "Aqui no ClickUp estão as tarefas da Sprint 2: criar a API com FastAPI, os
   > endpoints de candidatos e detalhe, substituir o JSON estático por `fetch()` no
   > front e recalcular os dados a partir do banco."
   - Mostre o board com as tarefas da Sprint 2.

3. **Código**
   - Abra `backend/main.py`.
   > "Esta é a API. Aqui estão os endpoints: `/api/carga`, que traz o resumo e a
   > série diária; `/api/candidatos`, que lista os candidatos; e
   > `/api/candidatos/{sq}`, que traz o detalhe por origem."
   - Abra a documentação automática em `http://127.0.0.1:8000/docs` (Swagger) e
     clique em um endpoint para mostrar a resposta JSON.
   - Abra `JS/data.js`.
   > "No front, o `JS/data.js` concentra as chamadas `fetch()`. Antes tínhamos um
   > JSON estático; agora tudo vem da API."

4. **Funcionalidade nova**
   - Abra o painel (`http://127.0.0.1:8000`).
   - Abra o DevTools (F12) na aba **Network**, atualize a página e mostre as
     chamadas `/api/carga` e `/api/candidatos`.
   > "Aqui dá para ver as chamadas à API. Os números do painel agora saem do
   > banco, via API."

5. **Fechamento**
   > "Essa foi a Sprint 2. Na próxima, a Sprint 3, vamos montar o banco de dados
   > dimensional e o ETL. Obrigado!"

---

## Vídeo 2 — Sprint 3: Banco de dados (entrega 08/11)

**Objetivo:** mostrar o modelo dimensional, o ETL e o controle de qualidade.

**Roteiro:**

1. **Abertura**
   > "Olá, sou [seu nome]. Este é o vídeo da Sprint 3, a entrega do banco de dados
   > do painel."

2. **Board (ClickUp)**
   > "As tarefas da Sprint 3 foram: modelar o banco dimensional, criar o schema e
   > as views, implementar o ETL do CSV do TSE e o controle de qualidade."
   - Mostre o board.

3. **Código**
   - Abra o diagrama MER (`diagramas/mer.svg` ou `DIAGRAMAS.md` no GitHub).
   > "O modelo é dimensional: a tabela fato `fato_despesa` ligada às dimensões
   > `dim_candidato`, `dim_fornecedor` e `dim_tempo`, mais a tabela `carga`, que
   > guarda os metadados da importação."
   - Abra `backend/etl.py`.
   > "Aqui está o ETL. Ele lê o CSV do TSE, converte os valores e as datas, e
   > popula a fato e as dimensões."
   - Abra `backend/schema.sql`.
   > "E aqui estão as views de apoio, como `vw_candidato_total`,
   > `vw_partido_total` e `vw_serie_diaria`."
   - Abra `backend/db.py`.
   > "O `db.py` roda o controle de qualidade, comparando contagem e soma."

4. **Funcionalidade nova**
   - Mostre o QC já executado (evite esperar o ETL completo, que leva ~3–4 min):
   > "Vou mostrar o resultado do controle de qualidade: 5 de 5 verificações OK —
   > linhas, soma total, soma por origem e candidatos."
   - Rode `python backend/db.py` ou abra `/api/qc` e mostre os itens com `OK`.

5. **Fechamento**
   > "Essa foi a Sprint 3. O banco dimensional está pronto e validado. Na entrega
   > final, vamos integrar tudo no painel. Obrigado!"

---

## Vídeo 3 — Entrega Final: Painel integrado (22/11)

**Objetivo:** mostrar a integração completa e as novas funcionalidades.

**Roteiro:**

1. **Abertura**
   > "Olá, sou [seu nome]. Este é o vídeo da entrega final do painel de despesas
   > contratadas de 2026."

2. **Board (ClickUp)**
   > "As tarefas da entrega final foram: filtro por período e categoria, painel por
   > cargo, visão geral por partido, atualização da carga, documentação e
   > publicação."
   - Mostre o board com as tarefas finais.

3. **Código**
   - Abra `index.html`.
   > "Aqui está o seletor de cargo e o menu com a visão de partidos."
   - Abra `JS/site.js`.
   > "No `site.js`, as funções `popularCargos`, `desenharPartidos` e
   > `atualizarEvolucao` implementam o seletor de cargo, a visão por partido e o
   > gráfico de evolução diária por partido."
   - Abra `backend/main.py`.
   > "No back, os endpoints `/api/cargos` e `/api/partidos` alimentam essas
   > visões."

4. **Funcionalidade nova**
   - Abra o painel e mostre a visão padrão (Presidente).
   - Troque o cargo para **Deputado Federal** no seletor e mostre os números
     mudando.
   > "Agora vou trocar o cargo e os números mudam conforme o cargo selecionado."
   - Abra a visão **Partidos** no menu e mostre o gráfico de custo por partido e a
     tabela.
   > "Esta é a visão geral por partido, com o gráfico e a tabela."
   - Mostre os filtros por período e categoria.
   - Abra a comparação entre dois candidatos.
   - Abra `DIAGRAMAS.md` no GitHub e mostre os diagramas.
   > "A documentação está no `METODOLOGIA.md` e os diagramas no `DIAGRAMAS.md`."
   - Mostre o link da Render.
   > "E o painel está publicado na Render, no link da descrição."

5. **Fechamento**
   > "Essa foi a entrega final: front, API e banco integrados, com todos os cargos,
   > visão por partido, filtros, documentação e deploy. Obrigado!"

---

## Dicas rápidas

- Fale olhando para a câmera na abertura e no fechamento.
- Mostre o **board → código → painel** nessa ordem.
- Não precisa mostrar tudo; foque no que foi implementado em cada sprint.
- Se o ETL demorar, mostre o resultado do QC em vez de esperar.
- Deixe o link do painel e do repositório na descrição do vídeo.