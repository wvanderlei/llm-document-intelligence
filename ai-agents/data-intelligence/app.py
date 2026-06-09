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

LOGO_PATH = os.path.join(os.path.dirname(__file__), "logo.png")

# ── CSS global ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

#MainMenu, footer, header { visibility: hidden; }

/* Fundo geral */
.stApp { background-color: #0a0f1e; }

/* Sidebar */
section[data-testid="stSidebar"] > div:first-child {
    background: #0d1526;
    border-right: 1px solid #1a2540;
    padding-top: 1.5rem;
}

/* Rótulos de seção */
.sec-label {
    font-size: 0.6rem;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #2d4a7a;
    margin: 1.2rem 0 0.5rem;
}

/* Botões de exemplo */
div[data-testid="stButton"] > button {
    background: #111827 !important;
    border: 1px solid #1e2d4a !important;
    border-radius: 8px !important;
    color: #7ea8d8 !important;
    font-size: 0.8rem !important;
    text-align: left !important;
    width: 100% !important;
    padding: 0.5rem 0.75rem !important;
    margin-bottom: 4px !important;
    transition: all 0.15s !important;
}
div[data-testid="stButton"] > button:hover {
    background: #162035 !important;
    border-color: #06b6d4 !important;
    color: #06b6d4 !important;
}

/* Hero */
.hero {
    background: linear-gradient(135deg, #0d1526 0%, #111827 60%, #0a1628 100%);
    border: 1px solid #1a2540;
    border-radius: 20px;
    padding: 2.5rem 3rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: "";
    position: absolute;
    top: -60px; right: -60px;
    width: 220px; height: 220px;
    background: radial-gradient(circle, rgba(6,182,212,0.12) 0%, transparent 70%);
    pointer-events: none;
}
.hero-eyebrow {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    color: #06b6d4;
    margin-bottom: 0.75rem;
}
.hero-title {
    font-size: 2.4rem;
    font-weight: 800;
    line-height: 1.15;
    margin: 0 0 0.75rem;
    background: linear-gradient(90deg, #f0f9ff 30%, #06b6d4 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.hero-sub {
    color: #64748b;
    font-size: 1rem;
    margin-bottom: 1.25rem;
    max-width: 600px;
}
.pill {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    background: rgba(6,182,212,0.08);
    border: 1px solid rgba(6,182,212,0.2);
    color: #67e8f9;
    padding: 0.3rem 0.8rem;
    border-radius: 100px;
    font-size: 0.72rem;
    font-weight: 500;
    margin-right: 0.5rem;
}

/* Métricas */
.metric-grid { display: flex; gap: 1rem; margin-bottom: 1.5rem; }
.mcard {
    flex: 1;
    background: #0d1526;
    border: 1px solid #1a2540;
    border-radius: 14px;
    padding: 1.4rem 1.5rem;
    text-align: center;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s;
}
.mcard:hover { border-color: #06b6d4; }
.mcard::after {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #3b82f6, #06b6d4);
}
.mval {
    font-size: 2.5rem;
    font-weight: 800;
    background: linear-gradient(135deg, #3b82f6, #06b6d4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.mlabel { font-size: 0.78rem; color: #475569; margin-top: 0.3rem; letter-spacing: 0.5px; }

/* Tech pills sidebar */
.tpill {
    display: inline-block;
    background: #111827;
    border: 1px solid #1e2d4a;
    color: #4a9abb;
    padding: 0.2rem 0.55rem;
    border-radius: 6px;
    font-size: 0.68rem;
    margin: 2px;
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
    return bq, st.secrets.get("GCP_PROJECT_ID", os.environ.get("GCP_PROJECT_ID"))


@st.cache_data(ttl=300)
def get_metrics(_bq, pid):
    try:
        qs = {
            "contratos": f"SELECT COUNT(*) n FROM `{pid}.datalyx_analytics.contratos`",
            "tickets":   f"SELECT COUNT(*) n FROM `{pid}.datalyx_analytics.tickets`",
            "pendentes": f"SELECT COUNT(*) n FROM `{pid}.datalyx_analytics.sla_metricas` WHERE resolvido=FALSE",
        }
        return {k: list(_bq.query(q).result())[0]["n"] for k, q in qs.items()}
    except Exception:
        return {"contratos": "—", "tickets": "—", "pendentes": "—"}


def build_schema(pid):
    return f"""Dataset BigQuery: `{pid}.datalyx_analytics`

contratos: cliente STRING, tipo STRING("recorrente"/"pontual"), valor_mensal FLOAT, status STRING, data_inicio DATE
tickets: id STRING, categoria STRING("incidente"/"duvida"/"manutencao"/"fora_de_escopo"), prioridade STRING("alta"/"media"/"baixa"), cliente STRING, data_abertura DATE
sla_metricas: ticket_id STRING, cliente STRING, categoria STRING, tempo_resposta_horas FLOAT, resolvido BOOL, data_resolucao DATE"""


def call_with_retry(fn, *args, **kwargs):
    while True:
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                m = re.search(r"retry in (\d+\.?\d*)s", str(e))
                wait = float(m.group(1)) + 2 if m else 65
                st.toast(f"Aguardando {wait:.0f}s (rate limit)...", icon="⏳")
                time.sleep(wait)
            else:
                raise


def ask(bq, pid, question):
    model = genai.GenerativeModel("gemini-2.5-flash")

    sql = call_with_retry(model.generate_content,
        f"SQL BigQuery apenas, sem markdown, primeira palavra SELECT ou WITH.\n{build_schema(pid)}\nPERGUNTA: {question}"
    ).text
    sql = re.sub(r"```sql\s*|```\s*", "", sql).strip()
    m = re.search(r"\b(SELECT|WITH)\b", sql, re.IGNORECASE)
    if m:
        sql = sql[m.start():]

    rows = [dict(r) for r in bq.query(sql).result()]
    if not rows:
        return "Nenhum resultado encontrado.", sql

    answer = call_with_retry(model.generate_content,
        f"Analista Datalyx. Responda em português, direto, máx 3 frases, sem SQL.\nPergunta: {question}\nDados: {rows[:15]}"
    ).text.strip()

    return answer, sql


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image(LOGO_PATH, width=160)

    st.markdown('<div class="sec-label">Sobre</div>', unsafe_allow_html=True)
    st.caption("Assistente que transforma perguntas em SQL, consulta o BigQuery e responde em linguagem natural.")

    st.markdown('<div class="sec-label">Exemplos</div>', unsafe_allow_html=True)
    examples = [
        "Quantos contratos temos?",
        "Qual a receita mensal total?",
        "Qual cliente abriu mais tickets?",
        "Incidentes de alta prioridade?",
        "Média de tempo de resposta?",
        "Tickets pendentes de resolução?",
    ]
    for ex in examples:
        if st.button(ex, key=f"ex_{ex}"):
            st.session_state["quick_q"] = ex

    st.markdown('<div class="sec-label">Stack</div>', unsafe_allow_html=True)
    st.markdown(
        '<span class="tpill">Gemini 2.5</span>'
        '<span class="tpill">BigQuery</span>'
        '<span class="tpill">Streamlit</span>'
        '<span class="tpill">Python</span>'
        '<span class="tpill">GCP</span>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sec-label">Repositório</div>', unsafe_allow_html=True)
    st.markdown("[![GitHub](https://img.shields.io/badge/GitHub-wvanderlei-0d1117?logo=github&style=flat-square)](https://github.com/wvanderlei/llm-document-intelligence)")


# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-eyebrow">Datalyx · Engenharia de Dados</div>
    <div class="hero-title">Data Intelligence Assistant</div>
    <div class="hero-sub">Faça perguntas em português sobre seus dados. O sistema gera o SQL, consulta o BigQuery e explica o resultado em linguagem de negócio.</div>
    <span class="pill">🤖 Gemini 2.5 Flash</span>
    <span class="pill">🗄️ BigQuery</span>
    <span class="pill">🐍 Python</span>
    <span class="pill">⚡ Real-time</span>
</div>
""", unsafe_allow_html=True)

# ── Métricas ──────────────────────────────────────────────────────────────────
try:
    bq, pid = get_clients()
    m = get_metrics(bq, pid)
    st.markdown(f"""
    <div class="metric-grid">
        <div class="mcard"><div class="mval">{m['contratos']}</div><div class="mlabel">Contratos ativos</div></div>
        <div class="mcard"><div class="mval">{m['tickets']}</div><div class="mlabel">Tickets de suporte</div></div>
        <div class="mcard"><div class="mval">{m['pendentes']}</div><div class="mlabel">Pendentes de resolução</div></div>
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
                answer, sql = ask(bq, pid, question)
                st.markdown(answer)
                with st.expander("Ver SQL gerado"):
                    st.code(sql, language="sql")
                st.session_state.messages.append({
                    "role": "assistant", "content": answer, "sql": sql,
                })
            except Exception as e:
                err = f"Erro: {e}"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})
