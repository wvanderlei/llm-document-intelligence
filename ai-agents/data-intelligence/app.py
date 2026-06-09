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

# ── Logo SVG ──────────────────────────────────────────────────────────────────
LOGO_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 52 52">
  <defs>
    <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#3b82f6"/>
      <stop offset="100%" stop-color="#06b6d4"/>
    </linearGradient>
  </defs>
  <polygon points="26,2 48,14 48,38 26,50 4,38 4,14" fill="url(#g)"/>
  <text x="26" y="34" text-anchor="middle" fill="white" font-size="22"
        font-weight="800" font-family="Arial, sans-serif">D</text>
</svg>
"""

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* --- Reset e base --- */
  #MainMenu, footer, header { visibility: hidden; }

  /* --- Header --- */
  .datalyx-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1.5rem 2rem;
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border-radius: 16px;
    border: 1px solid #334155;
    margin-bottom: 1.5rem;
  }
  .datalyx-brand { flex: 1; }
  .datalyx-brand h1 {
    margin: 0;
    font-size: 1.6rem;
    font-weight: 800;
    background: linear-gradient(90deg, #3b82f6, #06b6d4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  .datalyx-brand p {
    margin: 0.2rem 0 0.6rem;
    color: #94a3b8;
    font-size: 0.875rem;
  }
  .badge {
    display: inline-block;
    background: rgba(59,130,246,0.15);
    border: 1px solid rgba(59,130,246,0.3);
    color: #93c5fd;
    padding: 0.2rem 0.65rem;
    border-radius: 20px;
    font-size: 0.72rem;
    margin-right: 0.4rem;
    font-weight: 500;
  }

  /* --- Cards de métricas --- */
  .metric-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; }
  .metric-card {
    flex: 1;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    text-align: center;
    position: relative;
    overflow: hidden;
  }
  .metric-card::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #3b82f6, #06b6d4);
  }
  .metric-value {
    font-size: 2.2rem;
    font-weight: 800;
    background: linear-gradient(90deg, #3b82f6, #06b6d4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  .metric-label { font-size: 0.78rem; color: #64748b; margin-top: 0.2rem; }

  /* --- Sidebar --- */
  section[data-testid="stSidebar"] > div {
    background: #0f172a;
    border-right: 1px solid #1e293b;
  }
  .sidebar-logo {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 1rem 0 1.25rem;
    border-bottom: 1px solid #1e293b;
    margin-bottom: 1.25rem;
  }
  .sidebar-logo span {
    font-size: 1.1rem;
    font-weight: 700;
    background: linear-gradient(90deg, #3b82f6, #06b6d4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  .section-label {
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #475569;
    margin: 1.25rem 0 0.5rem;
  }
  .tech-pill {
    display: inline-block;
    background: rgba(59,130,246,0.1);
    border: 1px solid rgba(59,130,246,0.2);
    color: #93c5fd;
    padding: 0.2rem 0.6rem;
    border-radius: 6px;
    font-size: 0.72rem;
    margin: 0.2rem;
  }

  /* --- Botões de exemplo --- */
  .stButton > button {
    width: 100%;
    text-align: left !important;
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    color: #cbd5e1 !important;
    font-size: 0.82rem !important;
    padding: 0.55rem 0.8rem !important;
    transition: all 0.2s !important;
  }
  .stButton > button:hover {
    border-color: #3b82f6 !important;
    color: #93c5fd !important;
    background: rgba(59,130,246,0.1) !important;
  }
</style>
""", unsafe_allow_html=True)


# ── Auth ──────────────────────────────────────────────────────────────────────
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
            "contratos": f"SELECT COUNT(*) n FROM `{project_id}.datalyx_analytics.contratos`",
            "tickets":   f"SELECT COUNT(*) n FROM `{project_id}.datalyx_analytics.tickets`",
            "pendentes": f"SELECT COUNT(*) n FROM `{project_id}.datalyx_analytics.sla_metricas` WHERE resolvido = FALSE",
        }
        return {k: list(_bq_client.query(q).result())[0]["n"] for k, q in queries.items()}
    except Exception:
        return {"contratos": "—", "tickets": "—", "pendentes": "—"}


def build_schema(project_id):
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


def ask(bq_client, project_id, question):
    model = genai.GenerativeModel("gemini-2.5-flash")

    sql_prompt = f"""Você é especialista em SQL para BigQuery.
Gere APENAS o SQL que responde à pergunta. Sem explicações, sem markdown.
A primeira palavra deve ser SELECT ou WITH.

{build_schema(project_id)}

PERGUNTA: {question}"""

    resp = call_with_retry(model.generate_content, sql_prompt)
    sql = re.sub(r"```sql\s*|```\s*", "", resp.text).strip()
    m = re.search(r"\b(SELECT|WITH)\b", sql, re.IGNORECASE)
    if m:
        sql = sql[m.start():]

    rows = [dict(r) for r in bq_client.query(sql).result()]
    if not rows:
        return "Nenhum resultado encontrado.", sql

    explain_prompt = f"""Analista de negócios da Datalyx. Explique em português, direto, máx 3 frases. Sem SQL.
Pergunta: {question}
Resultado: {str(rows[:15])}"""

    resp2 = call_with_retry(model.generate_content, explain_prompt)
    return resp2.text.strip(), sql


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div class="sidebar-logo">
      {LOGO_SVG}
      <span>Datalyx</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-label">Sobre</div>', unsafe_allow_html=True)
    st.markdown(
        "<span style='color:#94a3b8;font-size:0.85rem'>Assistente que transforma perguntas em português em queries SQL, "
        "executa no BigQuery e explica o resultado em linguagem de negócio.</span>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-label">Exemplos</div>', unsafe_allow_html=True)
    examples = [
        "Quantos contratos temos?",
        "Qual a receita mensal total?",
        "Qual cliente abriu mais tickets?",
        "Quantos incidentes de alta prioridade?",
        "Qual a média de tempo de resposta?",
        "Quais tickets estão pendentes?",
    ]
    for ex in examples:
        if st.button(f"→ {ex}", key=f"ex_{ex}"):
            st.session_state["quick_q"] = ex

    st.markdown('<div class="section-label">Stack</div>', unsafe_allow_html=True)
    st.markdown("""
    <span class="tech-pill">Gemini 2.5 Flash</span>
    <span class="tech-pill">BigQuery</span>
    <span class="tech-pill">Streamlit</span>
    <span class="tech-pill">Python</span>
    <span class="tech-pill">GCP</span>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-label">Repositório</div>', unsafe_allow_html=True)
    st.markdown(
        "[![GitHub](https://img.shields.io/badge/GitHub-wvanderlei-black?logo=github&style=flat)](https://github.com/wvanderlei/llm-document-intelligence)"
    )


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="datalyx-header">
  {LOGO_SVG}
  <div class="datalyx-brand">
    <h1>Data Intelligence Assistant</h1>
    <p>Faça perguntas em português. O sistema gera SQL, consulta o BigQuery e explica o resultado.</p>
    <span class="badge">🤖 Gemini 2.5 Flash</span>
    <span class="badge">🗄️ BigQuery</span>
    <span class="badge">🐍 Python</span>
    <span class="badge">📊 Datalyx · Engenharia de Dados</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Métricas ──────────────────────────────────────────────────────────────────
try:
    bq_client, project_id = get_clients()
    m = get_metrics(bq_client, project_id)

    st.markdown(f"""
    <div class="metric-row">
      <div class="metric-card">
        <div class="metric-value">{m['contratos']}</div>
        <div class="metric-label">Contratos ativos</div>
      </div>
      <div class="metric-card">
        <div class="metric-value">{m['tickets']}</div>
        <div class="metric-label">Tickets de suporte</div>
      </div>
      <div class="metric-card">
        <div class="metric-value">{m['pendentes']}</div>
        <div class="metric-label">Pendentes de resolução</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Erro ao conectar: {e}")
    st.stop()

# ── Chat ──────────────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "Olá! Pode perguntar sobre contratos, tickets ou métricas de atendimento. Use os exemplos na barra lateral ou escreva sua própria pergunta.",
    }]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "sql" in msg:
            with st.expander("Ver SQL gerado"):
                st.code(msg["sql"], language="sql")

question = st.chat_input("Ex: Qual cliente tem mais incidentes de alta prioridade?")
if "quick_q" in st.session_state:
    question = st.session_state.pop("quick_q")

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
                    "role": "assistant", "content": answer, "sql": sql,
                })
            except Exception as e:
                err = f"Erro ao processar: {e}"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})
