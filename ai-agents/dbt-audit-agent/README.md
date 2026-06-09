# Projeto 5 — dbt Audit Agent

Agente autônomo que analisa falhas em pipelines dbt, diagnostica a causa raiz e entrega o SQL corrigido — sem intervenção humana.

## O que resolve

Um pipeline dbt quebrando às 3h da manhã significa: alguém ser acordado, abrir o terminal, ler logs, entender qual modelo falhou, investigar o schema da tabela, identificar o problema e corrigir o SQL. Este agente faz tudo isso sozinho. Você recebe o diagnóstico e o código pronto para aplicar.

## O que diferencia um agente de um script

Um script faz sempre os mesmos passos. Um agente **decide** quais ferramentas usar com base no que encontra. Se o erro é de coluna ausente, ele verifica o schema. Se é de dependência quebrada, ele lista os modelos. Cada problema pode seguir um caminho diferente.

## Ferramentas disponíveis

| Ferramenta | O que faz |
|------------|-----------|
| `ler_log(arquivo)` | Lê o log de erro do dbt |
| `ler_modelo(nome)` | Lê o SQL de um modelo específico |
| `listar_modelos()` | Lista todos os modelos do projeto |
| `verificar_schema(tabela)` | Retorna as colunas disponíveis em uma tabela |

## Cenário de demonstração

O projeto dbt incluído tem 4 modelos (2 staging, 2 marts). O modelo `fct_receita` referencia a coluna `valor_bruto` que foi renomeada para `valor_total` na tabela de origem — um erro clássico de breaking change.

## Como rodar

### 1. Criar ambiente e instalar dependências

```bash
cd ai-agents/dbt-audit-agent
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente

Copie o `.env.example` da raiz e preencha com sua `GEMINI_API_KEY`.

### 3. Executar o agente

```bash
python src/agent.py
```

O agente aguarda automaticamente o rate limit do free tier (5 req/min) entre cada chamada.

## Exemplo de saída

```
AGENTE DE AUDITORIA DBT — DATALYX
[QUOTA] 0/1500 requisições usadas hoje (0%)

Iniciando analise do pipeline...

  [tool] ler_log('error_log.txt')
  [tool] ler_modelo('fct_receita')
  [tool] verificar_schema('stg_pedidos')

RESULTADO DA ANALISE:

DIAGNÓSTICO:
O modelo fct_receita falhou porque referencia a coluna valor_bruto,
que não existe em stg_pedidos. O schema indica que a coluna correta é valor_total.

SOLUÇÃO:
SELECT
    p.id_pedido, p.data_pedido, p.id_cliente,
    c.nome_cliente, c.segmento,
    p.valor_total,
    p.valor_total * 0.9 AS valor_liquido,
    p.canal_venda
FROM {{ ref('stg_pedidos') }} p
LEFT JOIN {{ ref('stg_clientes') }} c ON p.id_cliente = c.id_cliente

IMPACTO:
Nenhum outro modelo dbt é afetado. Dashboards que usam valor_bruto
precisarão ser ajustados para valor_total.
```

## Stack

- [Google Gemini API](https://ai.google.dev/) — `gemini-2.5-flash` com function calling
- [python-dotenv](https://github.com/theskumar/python-dotenv)
