import os
import re
import sys
import time

import google.generativeai as genai
from google.cloud import bigquery
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from quota_tracker import track, status as quota_status

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

SCHEMA = f"""Projeto BigQuery: `{PROJECT_ID}` | Dataset: `datalyx_analytics`

TABELAS DISPONÍVEIS:

`{PROJECT_ID}.datalyx_analytics.contratos`
  cliente STRING        — nome do cliente (Radar, Forja, Nexus)
  tipo STRING           — "recorrente" (mensalidade) ou "pontual" (projeto único)
  valor_mensal FLOAT    — valor em reais por mês
  status STRING         — "ativo"
  data_inicio DATE      — data de início do contrato

`{PROJECT_ID}.datalyx_analytics.tickets`
  id STRING             — identificador (ex: TKT-0001)
  texto STRING          — descrição do ticket
  categoria STRING      — "incidente", "duvida", "manutencao", "fora_de_escopo"
  prioridade STRING     — "alta", "media", "baixa"
  cliente STRING        — nome do cliente
  data_abertura DATE    — data de abertura

`{PROJECT_ID}.datalyx_analytics.sla_metricas`
  ticket_id STRING          — referência ao ticket
  cliente STRING            — nome do cliente
  categoria STRING          — categoria do ticket
  tempo_resposta_horas FLOAT — horas até a primeira resposta
  resolvido BOOL            — se foi resolvido/encaminhado
  data_resolucao DATE       — data de resolução (NULL se pendente)"""

SQL_SYSTEM = f"""Você é um especialista em SQL para BigQuery.
Dado o schema abaixo, gere APENAS o SQL que responde à pergunta.
Responda somente com SQL puro, sem explicações, sem blocos markdown.

{SCHEMA}"""

EXPLAIN_SYSTEM = """Você é um analista de negócios da Datalyx.
Explique o resultado da query em português, de forma direta e orientada a decisão.
Máximo 3 frases. Não mencione SQL."""


def _call_with_retry(fn, *args, **kwargs):
    while True:
        try:
            track()
            return fn(*args, **kwargs)
        except Exception as e:
            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                match = re.search(r"retry in (\d+\.?\d*)s", str(e))
                wait = float(match.group(1)) + 2 if match else 65
                print(f"  aguardando rate limit ({wait:.0f}s)...")
                time.sleep(wait)
            else:
                raise


def generate_sql(model: genai.GenerativeModel, question: str) -> str:
    response = _call_with_retry(
        model.generate_content,
        f"PERGUNTA: {question}"
    )
    sql = response.text.strip()
    sql = re.sub(r"```sql\s*", "", sql)
    sql = re.sub(r"```\s*", "", sql)
    return sql.strip()


def run_query(client: bigquery.Client, sql: str) -> list[dict]:
    return [dict(row) for row in client.query(sql).result()]


def explain(model: genai.GenerativeModel, question: str, rows: list[dict]) -> str:
    result_preview = str(rows[:15])
    response = _call_with_retry(
        model.generate_content,
        f"Pergunta: {question}\nResultado: {result_preview}"
    )
    return response.text.strip()


def main():
    print("=" * 60)
    print("DATA INTELLIGENCE ASSISTANT — DATALYX")
    print("=" * 60)
    quota_status()

    bq_client = bigquery.Client(project=PROJECT_ID)
    sql_model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=SQL_SYSTEM)
    explain_model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=EXPLAIN_SYSTEM)

    print("\nConectado. Digite sua pergunta ou 'sair'.\n")

    while True:
        try:
            question = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando.")
            break

        if not question or question.lower() in ("sair", "exit", "q"):
            print("Encerrando.")
            break

        try:
            print("  gerando SQL...")
            sql = generate_sql(sql_model, question)
            print(f"  >> {sql[:100].replace(chr(10), ' ')}...")

            print("  executando no BigQuery...")
            rows = run_query(bq_client, sql)

            if not rows:
                print("Assistente: Nenhum resultado encontrado para essa pergunta.\n")
                continue

            print("  interpretando resultado...")
            answer = explain(explain_model, question, rows)
            print(f"\nAssistente: {answer}\n")

        except Exception as e:
            print(f"  Erro: {e}\n")


if __name__ == "__main__":
    main()
