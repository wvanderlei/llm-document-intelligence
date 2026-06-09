import os
import re
import time
import warnings
import streamlit as st
import google.generativeai as genai
from google.cloud import bigquery
from google.oauth2 import service_account

warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="Data Intelligence — Datalyx",
    page_icon="💬",
    layout="centered",
)

st.title("💬 Data Intelligence Assistant")
st.caption("Faça perguntas em português sobre os dados da Datalyx.")


@st.cache_resource
def get_clients():
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

    if "gcp_service_account" in st.secrets:
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"]
        )
        bq = bigquery.Client(credentials=creds, project=st.secrets["GCP_PROJECT_ID"])
    else:
        bq = bigquery.Client(project=os.environ.get("GCP_PROJECT_ID"))

    project_id = st.secrets.get("GCP_PROJECT_ID", os.environ.get("GCP_PROJECT_ID"))
    return bq, project_id


def build_schema(project_id: str) -> str:
    return f"""Projeto BigQuery: `{project_id}` | Dataset: `datalyx_analytics`

TABELAS:

`{project_id}.datalyx_analytics.contratos`
  cliente STRING, tipo STRING ("recorrente"/"pontual"), valor_mensal FLOAT, status STRING, data_inicio DATE

`{project_id}.datalyx_analytics.tickets`
  id STRING, texto STRING, categoria STRING ("incidente"/"duvida"/"manutencao"/"fora_de_escopo"),
  prioridade STRING ("alta"/"media"/"baixa"), cliente STRING, data_abertura DATE

`{project_id}.datalyx_analytics.sla_metricas`
  ticket_id STRING, cliente STRING, categoria STRING,
  tempo_resposta_horas FLOAT, resolvido BOOL, data_resolucao DATE"""


def call_with_retry(fn, *args, **kwargs):
    while True:
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                match = re.search(r"retry in (\d+\.?\d*)s", str(e))
                wait = float(match.group(1)) + 2 if match else 65
                st.toast(f"Rate limit atingido. Aguardando {wait:.0f}s...", icon="⏳")
                time.sleep(wait)
            else:
                raise


def generate_sql(model, schema: str, question: str) -> str:
    prompt = f"""Você é especialista em SQL para BigQuery.
Com base no schema abaixo, gere APENAS o SQL que responde à pergunta.
Responda somente com SQL puro, sem explicações, sem comentários, sem markdown.
A primeira palavra da resposta deve ser SELECT ou WITH.

{schema}

PERGUNTA: {question}"""
    response = call_with_retry(model.generate_content, prompt)
    sql = response.text.strip()
    sql = re.sub(r"```sql\s*", "", sql)
    sql = re.sub(r"```\s*", "", sql)
    sql = sql.strip()

    # Garante que começa no SELECT ou WITH, descartando qualquer texto antes
    match = re.search(r"\b(SELECT|WITH)\b", sql, re.IGNORECASE)
    if match:
        sql = sql[match.start():]

    return sql.strip()


def run_query(bq_client, sql: str) -> list[dict]:
    return [dict(row) for row in bq_client.query(sql).result()]


def explain(model, question: str, rows: list[dict]) -> str:
    prompt = f"""Você é um analista de negócios da Datalyx.
Explique o resultado abaixo em português, de forma direta e orientada a decisão.
Máximo 3 frases. Não mencione SQL.

Pergunta: {question}
Resultado: {str(rows[:15])}"""
    response = call_with_retry(model.generate_content, prompt)
    return response.text.strip()


# --- Inicializa sessão ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "content": "Olá! Pode me perguntar sobre contratos, tickets de suporte ou métricas de atendimento da Datalyx.",
    })

# --- Exibe histórico ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "sql" in msg:
            with st.expander("SQL gerado"):
                st.code(msg["sql"], language="sql")

# --- Input ---
question = st.chat_input("Ex: Qual cliente abriu mais incidentes?")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Analisando..."):
            try:
                bq_client, project_id = get_clients()
                schema = build_schema(project_id)
                model = genai.GenerativeModel("gemini-2.5-flash")

                sql = generate_sql(model, schema, question)
                rows = run_query(bq_client, sql)

                if not rows:
                    answer = "Nenhum resultado encontrado para essa pergunta."
                else:
                    answer = explain(model, question, rows)

                st.markdown(answer)
                with st.expander("SQL gerado"):
                    st.code(sql, language="sql")

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sql": sql,
                })

            except Exception as e:
                error_msg = f"Erro ao processar: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                })
