# Projeto 1 — Contract Analyzer

Lê um contrato em PDF e responde perguntas em linguagem natural usando Google Gemini.

## O que resolve

Contratos de consultoria têm dezenas de páginas com cláusulas técnicas. Encontrar uma informação específica — prazo, valor, condição de rescisão — exige leitura manual. Este projeto automatiza esse processo: você faz a pergunta, o modelo lê o contrato e responde.

## Como funciona

```
PDF → PyMuPDF (extração de texto) → Gemini (prompt + texto completo) → Resposta
```

O texto do contrato é enviado integralmente ao modelo junto com a pergunta. O modelo responde baseado exclusivamente no conteúdo do documento.

## Como rodar

### 1. Criar ambiente e instalar dependências

```bash
cd api-prompt-engineering/contract-analyzer
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente

Copie o `.env.example` da raiz do projeto e preencha com sua `GEMINI_API_KEY`.

### 3. Adicionar o PDF

Coloque o arquivo PDF na pasta `contracts/`.

### 4. Executar

```bash
python src/analyzer.py --file contracts/contrato.pdf --question "Qual é o prazo de vigência?"
```

## Exemplo de saída

```
Lendo contrato: contracts/Datalyx_Contrato_Radar.pdf
Texto extraído: 4.832 caracteres

Pergunta: Qual é o valor mensal do contrato?

RESPOSTA:
O contrato prevê uma mensalidade de R$ 12.500,00 pagável até o 5º dia útil de cada mês,
conforme cláusula 4.2.
```

## Stack

- [PyMuPDF](https://pymupdf.readthedocs.io/) — extração de texto de PDFs
- [Google Gemini API](https://ai.google.dev/) — `gemini-2.5-flash`
- [python-dotenv](https://github.com/theskumar/python-dotenv)
