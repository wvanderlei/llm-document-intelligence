# Projeto 4 — Ticket Classifier

Classifica automaticamente tickets de suporte por categoria e prioridade usando Scikit-learn.

## O que resolve

Com contrato de suporte ativo, os clientes abrem tickets misturados: incidentes críticos, dúvidas simples, ajustes pequenos e pedidos que nem estão no escopo do contrato. Triagem manual não escala. Este classificador roteia automaticamente cada ticket para o tratamento correto — e sinaliza quando uma demanda deveria virar uma nova proposta comercial.

## Categorias

| Categoria | Descrição | Ação |
|-----------|-----------|------|
| `incidente` | Algo parou ou está errado em produção | Time técnico, prioridade pela urgência |
| `duvida` | Orientação sobre algo já entregue | Pode ser respondido com RAG (Projeto 3) |
| `manutencao` | Ajuste dentro do escopo do contrato | Fila de manutenção |
| `fora_de_escopo` | Nova demanda não prevista no contrato | Time comercial — nova proposta |

## Como funciona

```
Treino:
tickets.csv (125 exemplos) → TF-IDF (1-2 gramas) → Regressão Logística → modelo salvo

Predição:
Texto do ticket → TF-IDF → modelo → categoria + prioridade + confiança
```

Dois classificadores independentes: um para categoria, outro para prioridade. Isso permite que cada um aprenda os padrões específicos do seu alvo.

## Como rodar

### 1. Criar ambiente e instalar dependências

```bash
cd rag-vector-search/ticket-classifier
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Treinar o modelo

```bash
python src/train.py
```

Exibe as métricas de avaliação (precision, recall, f1) e salva os modelos em `models/`.

### 3. Classificar um ticket

```bash
python src/predict.py --text "o pipeline de ETL parou ontem à noite, dados não chegaram no BigQuery"
```

## Exemplo de saída

```
CLASSIFICAÇÃO DO TICKET

Ticket: o pipeline de ETL parou ontem à noite, dados não chegaram no BigQuery

Categoria  : Incidente — algo parou ou está errado em produção
Prioridade : Alta  — responder em até 4h

Confiança por categoria:
  incidente            ##########           52%
  manutencao           ####                 21%
  fora_de_escopo       ###                  15%
  duvida               ##                   12%

>> Acao: acionar responsavel tecnico imediatamente.
```

## Limitações conhecidas

O modelo foi treinado com 125 exemplos sintéticos — suficiente para demonstrar o conceito, mas a confiança de predição é baixa (~40-65%). Em produção, 500+ tickets reais com labels corretos melhorariam significativamente a acurácia.

## Stack

- [Scikit-learn](https://scikit-learn.org/) — TF-IDF + Regressão Logística + Pipeline
- [Pandas](https://pandas.pydata.org/) — carregamento e manipulação dos dados
- [joblib](https://joblib.readthedocs.io/) — serialização dos modelos treinados
