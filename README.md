# LLM Document Intelligence

Portfolio de projetos de LLM e IA aplicados a problemas reais de uma empresa de consultoria em dados.

Cada projeto resolve um problema operacional concreto — do mais simples ao mais avançado. A progressão vai desde análise de contratos com prompt engineering até agentes autônomos que diagnosticam falhas em pipelines de dados.

---

## Contexto de negócio

Os projetos usam como base a **Datalyx**, uma consultoria especializada em engenharia de dados com clientes reais (Radar, Forja, Nexus). Cada cliente tem contratos ativos, abre tickets de suporte e depende de pipelines que precisam de monitoramento.

Esse cenário foi escolhido por refletir situações que qualquer empresa de dados enfrenta: volume crescente de contratos, equipe sobrecarregada com suporte, pipelines quebrando fora do horário, gestores pedindo análises em cima da hora.

---

## Os 6 projetos

| # | Projeto | O que resolve | Fase |
|---|---------|---------------|------|
| 1 | [Contract Analyzer](api-prompt-engineering/contract-analyzer/) | Analisa um contrato em PDF e responde perguntas em linguagem natural | Iniciante |
| 2 | [Report Generator](api-prompt-engineering/report-generator/) | Extrai dados dos contratos, carrega no BigQuery e gera relatório executivo automaticamente | Iniciante |
| 3 | [RAG — Document Q&A](rag-vector-search/rag-docs/) | Indexa a documentação técnica entregue aos clientes e responde dúvidas com citação de fonte | Intermediário |
| 4 | [Ticket Classifier](rag-vector-search/ticket-classifier/) | Classifica tickets de suporte por categoria e prioridade, sinalizando o que está fora do escopo do contrato | Intermediário |
| 5 | [dbt Audit Agent](ai-agents/dbt-audit-agent/) | Agente autônomo que lê logs de erro do dbt, diagnostica a causa raiz e entrega o SQL corrigido | Avançado |
| 6 | [Data Intelligence Assistant](ai-agents/data-intelligence/) | Responde perguntas de negócio em português consultando os dados do BigQuery com SQL gerado por LLM | Avançado |

---

## Como as fases se conectam

```
Fase 1 — Antes e depois do projeto
  O LLM lê contratos, extrai dados e gera relatórios.
  Resolve: tempo gasto com documentação manual.

Fase 2 — Durante a operação
  O RAG responde dúvidas dos clientes sobre o que foi entregue.
  O classificador roteia e prioriza tickets automaticamente.
  Resolve: triagem manual de suporte e perguntas repetitivas.

Fase 3 — Monitoramento contínuo
  O agente detecta e diagnostica falhas em pipelines sem intervenção humana.
  O assistente responde qualquer pergunta de negócio consultando os dados.
  Resolve: plantão noturno para pipelines e análises ad-hoc para gestão.
```

---

## Stack

| Categoria | Tecnologias |
|-----------|-------------|
| LLM | Google Gemini API — `gemini-2.5-flash` |
| Embeddings | `text-embedding-004` via Google AI Studio |
| Cloud | Google Cloud Platform — BigQuery |
| Vector Store | ChromaDB (local) |
| ML | Scikit-learn, Pandas, joblib |
| PDF | PyMuPDF |
| Agents | Function calling / tool use (Gemini) |
| Linguagem | Python 3.11+ |

---

## Pré-requisitos

- Python 3.11+
- [Google AI Studio API Key](https://aistudio.google.com) — free tier (1.500 req/dia)
- Google Cloud SDK com `application-default login` — necessário apenas nos projetos com BigQuery (2, 3, 6)
- Projeto GCP com BigQuery ativo

---

## Configuração

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/llm-document-intelligence.git
cd llm-document-intelligence
```

### 2. Configure as variáveis de ambiente

```bash
cp .env.example .env
```

Preencha o `.env`:

```env
GEMINI_API_KEY=AIza...          # Google AI Studio — free tier
GCP_PROJECT_ID=seu-projeto-id   # ID do projeto no Google Cloud
GCP_REGION=us-central1
```

### 3. Autentique no Google Cloud (projetos 2, 3 e 6)

```bash
gcloud auth application-default login
```

---

## Como rodar cada projeto

Cada projeto é independente com seu próprio ambiente virtual. O padrão é:

```bash
cd <caminho-do-projeto>
python -m venv .venv
.venv\Scripts\activate        # Windows
# ou
source .venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
python src/<script>.py
```

Consulte o `README.md` de cada projeto para instruções específicas.

---

## Quota tracker

Todos os projetos compartilham o arquivo `quota_tracker.py` na raiz. Ele registra cada chamada à API Gemini em um arquivo local (`.quota.json`), exibe o consumo no início de cada execução e bloqueia automaticamente ao atingir o limite diário de 1.500 requisições.

---

## Estrutura do repositório

```
llm-document-intelligence/
│
├── api-prompt-engineering/
│   ├── contract-analyzer/      # Projeto 1
│   └── report-generator/       # Projeto 2
│
├── rag-vector-search/
│   ├── rag-docs/               # Projeto 3
│   └── ticket-classifier/      # Projeto 4
│
├── ai-agents/
│   ├── dbt-audit-agent/        # Projeto 5
│   └── data-intelligence/      # Projeto 6
│
├── quota_tracker.py            # Controle de uso da API
├── .env.example
├── .gitignore
└── README.md
```

---

## Autor

**Waydson Barros** — Engenheiro de dados com foco em aplicações de LLM e arquiteturas modernas de dados no Google Cloud.
