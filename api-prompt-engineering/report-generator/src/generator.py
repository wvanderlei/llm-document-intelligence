import os
import sys
import json
import glob
from datetime import date

import fitz  # PyMuPDF
import google.generativeai as genai
from google.cloud import bigquery
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from quota_tracker import track, status

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
DATASET_ID = "datalyx_analytics"
TABLE_ID = "contratos"
CONTRACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "contract-analyzer", "contracts")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")

SCHEMA = [
    bigquery.SchemaField("cliente", "STRING"),
    bigquery.SchemaField("tipo", "STRING"),
    bigquery.SchemaField("valor_mensal", "FLOAT"),
    bigquery.SchemaField("status", "STRING"),
    bigquery.SchemaField("data_inicio", "DATE"),
    bigquery.SchemaField("arquivo_origem", "STRING"),
]


# ── BigQuery ──────────────────────────────────────────────────────────────────

def setup_bigquery(client: bigquery.Client):
    dataset_ref = bigquery.Dataset(f"{PROJECT_ID}.{DATASET_ID}")
    dataset_ref.location = "US"
    try:
        client.create_dataset(dataset_ref)
        print(f"Dataset '{DATASET_ID}' criado.")
    except Exception:
        print(f"Dataset '{DATASET_ID}' já existe.")

    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    try:
        client.create_table(bigquery.Table(table_ref, schema=SCHEMA))
        print(f"Tabela '{TABLE_ID}' criada.")
    except Exception:
        print(f"Tabela '{TABLE_ID}' já existe.")


def load_contracts(client: bigquery.Client, contracts: list[dict]):
    """Substitui toda a tabela com os dados atuais — evita duplicatas."""
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

    rows = [
        {
            "cliente": c.get("cliente", ""),
            "tipo": c.get("tipo", ""),
            "valor_mensal": float(c.get("valor_mensal", 0)),
            "status": c.get("status", "ativo"),
            "data_inicio": c.get("data_inicio", str(date.today())),
            "arquivo_origem": c.get("arquivo_origem", ""),
        }
        for c in contracts
    ]

    job_config = bigquery.LoadJobConfig(
        schema=SCHEMA,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    job = client.load_table_from_json(rows, table_ref, job_config=job_config)
    job.result()

    print(f"{len(rows)} contrato(s) carregado(s) no BigQuery.")
    for r in rows:
        print(f"  >> {r['cliente']} ({r['tipo']}) | R$ {r['valor_mensal']:,.2f}/mes")


def get_metrics(client: bigquery.Client) -> dict:
    query = f"""
        SELECT
            COUNT(*) AS total_contratos,
            COUNTIF(tipo = 'recorrente') AS contratos_recorrentes,
            COUNTIF(tipo = 'pontual') AS contratos_pontuais,
            SUM(valor_mensal) AS receita_total_mensal,
            SUM(IF(tipo = 'recorrente', valor_mensal, 0)) AS receita_recorrente,
            SUM(IF(tipo = 'pontual', valor_mensal, 0)) AS receita_pontual
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
        WHERE status = 'ativo'
    """
    result = client.query(query).result()
    row = next(iter(result))
    return dict(row)


# ── Gemini ────────────────────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(pages)


def extract_all_contracts(pdf_files: list[str]) -> list[dict]:
    """Extrai dados de todos os PDFs em uma única chamada ao Gemini."""
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-2.5-flash")

    contracts_text = ""
    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        text = extract_text_from_pdf(pdf_path)
        contracts_text += f"\n\n=== ARQUIVO: {filename} ===\n{text}\n=== FIM: {filename} ==="

    prompt = f"""Analise os contratos abaixo e extraia os dados de cada um.

{contracts_text}

Retorne SOMENTE um JSON array válido, um objeto por contrato. Nenhum texto adicional.
Campos obrigatórios por contrato:
- cliente: nome do cliente/empresa contratante
- tipo: "recorrente" se tiver mensalidade contínua, "pontual" se for projeto com entrega única
- valor_mensal: valor numérico em reais (sem R$, sem pontos). Se pontual, use o valor total do projeto
- status: "ativo"
- data_inicio: data no formato YYYY-MM-DD (use 2024-01-01 se não encontrar)
- arquivo_origem: nome do arquivo correspondente

Exemplo de resposta válida:
[
  {{"cliente": "Empresa X", "tipo": "recorrente", "valor_mensal": 32400.0, "status": "ativo", "data_inicio": "2024-06-01", "arquivo_origem": "contrato_x.pdf"}},
  {{"cliente": "Empresa Y", "tipo": "pontual", "valor_mensal": 7000.0, "status": "ativo", "data_inicio": "2024-01-01", "arquivo_origem": "contrato_y.pdf"}}
]"""

    track()
    response = model.generate_content(prompt)
    raw = response.text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def generate_report(metrics: dict, contracts: list[dict]) -> str:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-2.5-flash")

    contracts_summary = "\n".join([
        f"- {c['cliente']} ({c['tipo']}): R$ {c['valor_mensal']:,.2f}/mês"
        for c in contracts
    ])

    prompt = f"""Você é um analista de negócios da Datalyx, empresa de consultoria em dados.
Gere um relatório executivo profissional em português com base nas métricas abaixo.

MÉTRICAS DO MÊS:
- Total de contratos ativos: {metrics['total_contratos']}
- Contratos recorrentes: {metrics['contratos_recorrentes']}
- Contratos pontuais: {metrics['contratos_pontuais']}
- Receita mensal total: R$ {metrics['receita_total_mensal']:,.2f}
- Receita recorrente: R$ {metrics['receita_recorrente']:,.2f}
- Receita pontual (projetos): R$ {metrics['receita_pontual']:,.2f}

DETALHAMENTO DOS CONTRATOS:
{contracts_summary}

O relatório deve ter:
1. Cabeçalho com data
2. Resumo executivo (2-3 parágrafos)
3. Destaques e pontos de atenção
4. Recomendações para o próximo período

Seja direto, profissional e oriente para tomada de decisão."""

    track()
    response = model.generate_content(prompt)
    return response.text


# ── Pipeline principal ────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("GERADOR DE RELATÓRIO DATALYX")
    print("=" * 60)

    bq_client = bigquery.Client(project=PROJECT_ID)
    setup_bigquery(bq_client)

    pdf_files = glob.glob(os.path.join(CONTRACTS_DIR, "*.pdf"))
    if not pdf_files:
        print(f"Nenhum PDF encontrado em: {CONTRACTS_DIR}")
        return

    status()
    print(f"\n{len(pdf_files)} contrato(s) encontrado(s). Extraindo dados com Gemini (1 chamada)...\n")

    contracts_data = extract_all_contracts(pdf_files)

    for data in contracts_data:
        print(f"Dados extraídos: {data}")
    print()

    load_contracts(bq_client, contracts_data)

    print("Consultando métricas no BigQuery...")
    metrics = get_metrics(bq_client)
    print(f"Métricas: {metrics}\n")

    print("Gerando relatório executivo com Gemini...")
    report = generate_report(metrics, contracts_data)

    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_path = os.path.join(REPORTS_DIR, f"relatorio_{date.today()}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nRelatório salvo em: {report_path}")
    print("\n" + "=" * 60)
    print(report)
    print("=" * 60)


if __name__ == "__main__":
    main()
