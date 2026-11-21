# Entrega — Painel de Despesas Contratadas 2026

Painel web (FastAPI + SQLite + Chart.js) de **despesa contratada declarada** por
candidatos nas eleições de 2026, a partir dos dados abertos do TSE.

## Repositório

https://github.com/cabralzin1/Projeto-faculdade

## Como executar (Windows)

1. Instale o **Python 3.12**.
2. Na pasta do projeto, execute `iniciar.bat` (cria o `.venv`, instala as
   dependências e sobe a API na porta 8000).
3. Abra **http://127.0.0.1:8000**.

## Acesso online (sem baixar o banco)

O painel pode ser hospedado na **Render** (plano gratuito) para acesso por URL.
O `render.yaml` já está no repositório:

1. Acesse https://render.com e crie a conta (pode entrar com GitHub).
2. **New → Blueprint** e selecione o repositório `cabralzin1/Projeto-faculdade`.
3. A Render lê o `render.yaml`, baixa o `campanha.db` da release e sobe a API.
4. A URL será algo como `https://painel-despesas-2026.onrender.com`.

Obs.: no plano gratuito a Render "dorme" após 15 min sem acesso; a primeira
requisição pode levar ~50 s.

## Banco de dados

O banco `Dados/campanha.db` (~672 MB) **não está no Git** (limite de 100 MB por
arquivo do GitHub). Baixe-o na release e coloque em `Dados/campanha.db`:

https://github.com/cabralzin1/Projeto-faculdade/releases/tag/v1.0.0-entrega

Se preferir gerar o banco, baixe o CSV do TSE e rode:

```bash
python backend/etl.py --csv "<caminho>/despesas_contratadas_candidatos_2026_BRASIL.csv"
```

## Fonte

TSE — Dados Abertos, Prestação de Contas Eleitorais 2026:
https://dadosabertos.tse.jus.br/dataset/prestacao-de-contas-eleitorais-2026

## Metodologia

Ver [METODOLOGIA.md](METODOLOGIA.md).