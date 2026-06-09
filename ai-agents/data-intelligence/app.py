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
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Fundo e fonte */
    .main { background-color: #f8f9fb; }

    /* Header */
    .header-container {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .header-title {
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
        color: white;
    }
    .header-subtitle {
        font-size: 1rem;
        color: #a0aec0;
        margin-top: 0.25rem;
    }
    .badge {
        display: inline-block;
        background: rgba(255,255,255,0.15);
        border: 1px solid rgba(255,255,255,0.2);
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        margin-right: 0.5rem;
        margin-top: 0.75rem;
    }

    /* Cards de métricas */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        border-left: 4px solid #0f3460;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #0f3460;
    }
    .metric-label {
        font-size: 0.8rem;
        color: #718096;
        margin-top: 0.25rem;
    }

    /* Botões de exemplo */
    .stButton > button {
        width: 100%;
        text-align: left;
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 0.6rem 0.8rem;
        color: #2d3748;
        font-size: 0.85rem;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        border-color: #0f3460;
        color: #0f3460;
        background: #ebf4ff;
    }

    /* Chat */
    .chat-area {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        min-height: 400px;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: white;
    }
    .sidebar-section {
        margin-bottom: 1.5rem;
    }
    .sidebar-title {
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #a0aec0;
        margin-bottom: 0.75rem;
    }
    .tech-badge {
        display: inline-block;
        background: #f0f4f8;
        color: #4a5568;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        font-size: 0.75rem;
        margin: 0.2rem;
    }

    /* Esconde footer padrão */
    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── Auth ─────────────────────────────────────────────────────────────────────
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


@st.cache_data(ttl=300)
def get_metrics(_bq_client, project_id):
    try:
        queries = {
            "contratos": f"SELECT COUNT(*) as n FROM `{project_id}.datalyx_analytics.contratos`",
            "tickets":   f"SELECT COUNT(*) as n FROM `{project_id}.datalyx_analytics.tickets`",
            "pendentes": f"SELECT COUNT(*) as n FROM `{project_id}.datalyx_analytics.sla_metricas` WHERE resolvido = FALSE",
        }
        results = {}
        for key, q in queries.items():
            row = list(_bq_client.query(q).result())[0]
            results[key] = row["n"]
        return results
    except Exception:
        return {"contratos": "—", "tickets": "—", "pendentes": "—"}


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
                st.toast(f"Aguardando rate limit ({wait:.0f}s)...", icon="⏳")
                time.sleep(wait)
            else:
                raise


def ask(bq_client, project_id, question: str) -> tuple[str, str]:
    model = genai.GenerativeModel("gemini-2.5-flash")
    schema = build_schema(project_id)

    sql_prompt = f"""Você é especialista em SQL para BigQuery.
Com base no schema abaixo, gere APENAS o SQL que responde à pergunta.
Responda somente com SQL puro, sem explicações, sem comentários, sem markdown.
A primeira palavra da resposta deve ser SELECT ou WITH.

{schema}

PERGUNTA: {question}"""

    response = call_with_retry(model.generate_content, sql_prompt)
    sql = response.text.strip()
    sql = re.sub(r"```sql\s*", "", sql)
    sql = re.sub(r"```\s*", "", sql).strip()
    match = re.search(r"\b(SELECT|WITH)\b", sql, re.IGNORECASE)
    if match:
        sql = sql[match.start():]

    rows = [dict(r) for r in bq_client.query(sql).result()]

    if not rows:
        return "Nenhum resultado encontrado para essa pergunta.", sql

    explain_prompt = f"""Você é um analista de negócios da Datalyx.
Explique o resultado abaixo em português, de forma direta e orientada a decisão.
Máximo 3 frases. Não mencione SQL.

Pergunta: {question}
Resultado: {str(rows[:15])}"""

    resp2 = call_with_retry(model.generate_content, explain_prompt)
    return resp2.text.strip(), sql


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 💬 Data Intelligence")
    st.markdown("---")

    st.markdown('<div class="sidebar-title">Sobre</div>', unsafe_allow_html=True)
    st.markdown("""
Assistente que responde perguntas de negócio em **português** consultando dados reais no BigQuery via SQL gerado por LLM.
""")

    st.markdown("---")
    st.markdown('<div class="sidebar-title">Exemplos de perguntas</div>', unsafe_allow_html=True)

    examples = [
        "Quantos contratos temos ativos?",
        "Qual a receita mensal total?",
        "Qual cliente abriu mais tickets?",
        "Quantos incidentes de alta prioridade temos?",
        "Qual a média de tempo de resposta por categoria?",
        "Quais tickets estão sem resolução?",
    ]

    for ex in examples:
        if st.button(ex, key=f"btn_{ex}"):
            st.session_state["quick_question"] = ex

    st.markdown("---")
    st.markdown('<div class="sidebar-title">Stack</div>', unsafe_allow_html=True)
    st.markdown("""
<span class="tech-badge">Gemini 2.5 Flash</span>
<span class="tech-badge">BigQuery</span>
<span class="tech-badge">Python</span>
<span class="tech-badge">Streamlit</span>
""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(
        "[![GitHub](https://img.shields.io/badge/GitHub-Repositório-black?logo=github)](https://github.com/wvanderlei/llm-document-intelligence)",
        unsafe_allow_html=True,
    )


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="header-container">
    <p class="header-title">💬 Data Intelligence Assistant</p>
    <p class="header-subtitle">Faça perguntas em português. O sistema gera o SQL, consulta o BigQuery e explica o resultado.</p>
    <span class="badge">🤖 Gemini 2.5 Flash</span>
    <span class="badge">🗄️ BigQuery</span>
    <span class="badge">🐍 Python</span>
    <span class="badge">📊 Datalyx</span>
</div>
""", unsafe_allow_html=True)

# ── Métricas ──────────────────────────────────────────────────────────────────
try:
    bq_client, project_id = get_clients()
    metrics = get_metrics(bq_client, project_id)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{metrics['contratos']}</div>
            <div class="metric-label">Contratos ativos</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{metrics['tickets']}</div>
            <div class="metric-label">Tickets de suporte</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{metrics['pendentes']}</div>
            <div class="metric-label">Tickets pendentes</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

except Exception as e:
    st.error(f"Erro ao conectar: {e}")
    st.stop()

# ── Chat ──────────────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "Olá! Pode me perguntar sobre contratos, tickets de suporte ou métricas de atendimento. Use os exemplos na barra lateral ou escreva sua própria pergunta.",
    }]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "sql" in msg:
            with st.expander("Ver SQL gerado"):
                st.code(msg["sql"], language="sql")

# Pergunta via botão lateral ou input direto
question = st.chat_input("Ex: Qual cliente tem mais incidentes de alta prioridade?")
if "quick_question" in st.session_state:
    question = st.session_state.pop("quick_question")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Analisando dados..."):
            try:
                answer, sql = ask(bq_client, project_id, question)
                st.markdown(answer)
                with st.expander("Ver SQL gerado"):
                    st.code(sql, language="sql")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sql": sql,
                })
            except Exception as e:
                msg = f"Erro ao processar: {e}"
                st.error(msg)
                st.session_state.messages.append({"role": "assistant", "content": msg})
