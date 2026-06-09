# Projeto 6 — Data Intelligence Assistant

Responde perguntas de negócio em linguagem natural consultando dados do BigQuery com SQL gerado por LLM.

## O que resolve

Gestores precisam de análises rápidas mas dependem do time técnico para escrever queries. Analistas passam horas em perguntas simples. Este assistente elimina esse gargalo: qualquer pessoa pergunta em português, o sistema gera o SQL, executa no BigQuery e responde com os dados reais.

## Como funciona

```
Pergunta em português
  ↓
LLM recebe a pergunta + schema das 3 tabelas
  ↓
LLM gera o SQL correto para BigQuery
  ↓
Query executada no BigQuery
  ↓
LLM explica o resultado em linguagem de negócio
  ↓
Resposta ao usuário
```

## Dados disponíveis

| Tabela | Conteúdo |
|--------|----------|
| `contratos` | Clientes, tipo de contrato, valor mensal, data de início |
| `tickets` | 125 tickets de suporte com categoria, prioridade e data |
| `sla_metricas` | Tempo de resposta, resolução e data de fechamento por ticket |

## Como rodar

### 1. Criar ambiente e instalar dependências

```bash
cd ai-agents/data-intelligence
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Autenticar no Google Cloud

```bash
gcloud auth application-default login
```

### 3. Carregar os dados no BigQuery (roda uma vez)

```bash
python src/setup_data.py
```

### 4. Iniciar o assistente

```bash
python src/assistant.py
```

## Exemplos de perguntas

```
Você: qual cliente abriu mais incidentes?
Você: qual a receita mensal total dos contratos recorrentes?
Você: quantos tickets de alta prioridade estão sem resolução?
Você: qual a média de tempo de resposta por categoria?
Você: quais tickets foram abertos nos últimos 30 dias?
```

## Exemplo de saída

```
DATA INTELLIGENCE ASSISTANT — DATALYX
[QUOTA] 0/1500 requisições usadas hoje (0%)

Conectado. Digite sua pergunta ou 'sair'.

Você: qual cliente abriu mais incidentes?
  gerando SQL...
  >> SELECT cliente, COUNT(*) as total FROM `projeto.datalyx_analytics.tickets` WHERE catego...
  executando no BigQuery...
  interpretando resultado...

Assistente: O cliente Forja liderou em número de incidentes com 14 ocorrências,
seguido por Radar com 12. Isso indica que o Forja pode demandar atenção
especial na próxima revisão de contrato de suporte.
```

## Stack

- [Google Gemini API](https://ai.google.dev/) — `gemini-2.5-flash` para geração de SQL e explicação
- [Google Cloud BigQuery](https://cloud.google.com/bigquery) — execução das queries
- [Pandas](https://pandas.pydata.org/) — preparação dos dados de setup
- [python-dotenv](https://github.com/theskumar/python-dotenv)
