# Projeto 2 — Report Generator

Lê contratos em PDF, extrai dados estruturados com Gemini, carrega no BigQuery e gera um relatório executivo em linguagem natural.

## O que resolve

Gerar um relatório de situação dos contratos exigia abrir cada PDF, copiar dados para uma planilha e escrever o texto. Com 3 clientes já é trabalhoso — com 15 seria inviável. Este projeto automatiza o pipeline completo: dos PDFs ao relatório pronto.

## Como funciona

```
PDFs
  ↓
Gemini extrai dados de todos os contratos em uma única chamada (JSON estruturado)
  ↓
BigQuery armazena os dados na tabela datalyx_analytics.contratos
  ↓
SQL agrega as métricas (receita total, contratos recorrentes vs pontuais)
  ↓
Gemini gera o relatório executivo em markdown
  ↓
Arquivo salvo em reports/relatorio_YYYY-MM-DD.md
```

## Como rodar

### 1. Criar ambiente e instalar dependências

```bash
cd api-prompt-engineering/report-generator
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Autenticar no Google Cloud

```bash
gcloud auth application-default login
```

### 3. Executar

```bash
python src/generator.py
```

O relatório será salvo em `reports/`.

## Exemplo de saída (trecho)

```
## Relatório Executivo — Datalyx
### Junho 2025

**Receita mensal total:** R$ 47.900,00
**Contratos ativos:** 3 (2 recorrentes, 1 pontual)

### Resumo
A base de clientes apresenta crescimento estável, com predominância
de contratos recorrentes representando 78% da receita total...
```

## Stack

- [PyMuPDF](https://pymupdf.readthedocs.io/) — extração de texto de PDFs
- [Google Gemini API](https://ai.google.dev/) — extração estruturada + geração de relatório
- [Google Cloud BigQuery](https://cloud.google.com/bigquery) — armazenamento e métricas
- [python-dotenv](https://github.com/theskumar/python-dotenv)
