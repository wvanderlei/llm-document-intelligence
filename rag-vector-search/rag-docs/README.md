# Projeto 3 — RAG Document Q&A

Indexa documentos técnicos entregues aos clientes e responde perguntas em linguagem natural com citação da fonte exata.

## O que resolve

Após um projeto finalizado, clientes continuam com dúvidas: "qual a regra de cálculo da margem?", "esse campo inclui devoluções?", "qual a frequência de atualização?". Hoje alguém do time precisa abrir o documento e responder. Com RAG, o próprio sistema responde — baseado exclusivamente na documentação entregue.

## Como funciona

```
Indexação (roda uma vez):
PDFs → chunks de 1.200 palavras → embeddings (text-embedding-004) → ChromaDB

Consulta:
Pergunta → embedding → busca top-2 chunks mais relevantes → Gemini gera resposta → fonte citada
```

O modelo só usa os trechos recuperados para responder. Se a informação não estiver nos documentos, ele informa claramente.

## Como rodar

### 1. Criar ambiente e instalar dependências

```bash
cd rag-vector-search/rag-docs
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente

Copie o `.env.example` da raiz e preencha com sua `GEMINI_API_KEY`.

### 3. Indexar os documentos (roda uma vez)

```bash
python src/indexer.py
```

Use `--force` para reindexar mesmo que já exista:

```bash
python src/indexer.py --force
```

### 4. Fazer perguntas

```bash
python src/chatbot.py --question "O contrato Nexus inclui suporte fora do horário comercial?"
```

## Exemplo de saída

```
Base de conhecimento: 12 chunks indexados

Pergunta: Qual o prazo de entrega do projeto Forja?

Encontrados 2 trechos. Gerando resposta...

RESPOSTA:
Conforme a cláusula 3.1, o prazo de entrega está estipulado em 90 dias corridos
a partir da data de assinatura do contrato, podendo ser prorrogado mediante
aditivo assinado por ambas as partes.

Fontes consultadas:
  - Contrato_Datalyx_Forja.pdf
```

## Stack

- [PyMuPDF](https://pymupdf.readthedocs.io/) — extração de texto de PDFs
- [ChromaDB](https://www.trychroma.com/) — banco vetorial local persistente
- [Google Gemini API](https://ai.google.dev/) — embeddings (`text-embedding-004`) + geração (`gemini-2.5-flash`)
- [python-dotenv](https://github.com/theskumar/python-dotenv)
