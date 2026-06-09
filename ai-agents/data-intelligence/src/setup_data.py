import os
import random
from datetime import date, datetime, timedelta

import pandas as pd
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
DATASET_ID = "datalyx_analytics"
TICKETS_CSV = os.path.join(
    os.path.dirname(__file__), "..", "..", "..",
    "rag-vector-search", "ticket-classifier", "data", "tickets.csv"
)

TICKETS_SCHEMA = [
    bigquery.SchemaField("id", "STRING"),
    bigquery.SchemaField("texto", "STRING"),
    bigquery.SchemaField("categoria", "STRING"),
    bigquery.SchemaField("prioridade", "STRING"),
    bigquery.SchemaField("cliente", "STRING"),
    bigquery.SchemaField("data_abertura", "DATE"),
]

SLA_SCHEMA = [
    bigquery.SchemaField("ticket_id", "STRING"),
    bigquery.SchemaField("cliente", "STRING"),
    bigquery.SchemaField("categoria", "STRING"),
    bigquery.SchemaField("tempo_resposta_horas", "FLOAT"),
    bigquery.SchemaField("resolvido", "BOOL"),
    bigquery.SchemaField("data_resolucao", "DATE"),
]

RESPONSE_HOURS = {
    ("incidente", "alta"):      (1, 4),
    ("incidente", "media"):     (4, 12),
    ("duvida", "baixa"):        (12, 36),
    ("duvida", "media"):        (8, 24),
    ("manutencao", "media"):    (24, 72),
    ("manutencao", "baixa"):    (48, 120),
    ("fora_de_escopo", "baixa"): (24, 72),
    ("fora_de_escopo", "media"): (12, 48),
}


def ensure_table(client: bigquery.Client, table_id: str, schema: list):
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{table_id}"
    try:
        client.create_table(bigquery.Table(table_ref, schema=schema))
        print(f"  Tabela '{table_id}' criada.")
    except Exception:
        print(f"  Tabela '{table_id}' já existe.")


def load_tickets(client: bigquery.Client) -> pd.DataFrame:
    random.seed(42)
    today = date.today()

    df = pd.read_csv(TICKETS_CSV)
    df["id"] = [f"TKT-{i + 1:04d}" for i in range(len(df))]
    df["data_abertura"] = [
        str(today - timedelta(days=random.randint(0, 180)))
        for _ in range(len(df))
    ]

    rows = df[["id", "texto", "categoria", "prioridade", "cliente", "data_abertura"]].to_dict("records")
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.tickets"
    job = client.load_table_from_json(
        rows, table_ref,
        job_config=bigquery.LoadJobConfig(
            schema=TICKETS_SCHEMA,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        ),
    )
    job.result()
    print(f"  {len(rows)} tickets carregados.")
    return df


def generate_and_load_sla(client: bigquery.Client, df: pd.DataFrame):
    random.seed(42)
    today = date.today()
    sla_rows = []

    for _, row in df.iterrows():
        key = (row["categoria"], row["prioridade"])
        min_h, max_h = RESPONSE_HOURS.get(key, (24, 72))
        tempo = round(random.uniform(min_h, max_h), 1)

        resolvido = row["categoria"] != "fora_de_escopo" or random.random() < 0.1
        abertura = date.fromisoformat(row["data_abertura"])
        if resolvido:
            dt_res = datetime(abertura.year, abertura.month, abertura.day) + timedelta(hours=tempo + random.uniform(1, 48))
            data_res = str(min(dt_res.date(), today))
        else:
            data_res = None

        sla_rows.append({
            "ticket_id": row["id"],
            "cliente": row["cliente"],
            "categoria": row["categoria"],
            "tempo_resposta_horas": tempo,
            "resolvido": resolvido,
            "data_resolucao": data_res,
        })

    table_ref = f"{PROJECT_ID}.{DATASET_ID}.sla_metricas"
    job = client.load_table_from_json(
        sla_rows, table_ref,
        job_config=bigquery.LoadJobConfig(
            schema=SLA_SCHEMA,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        ),
    )
    job.result()
    print(f"  {len(sla_rows)} registros de SLA carregados.")


def main():
    print("=" * 60)
    print("SETUP — DATA INTELLIGENCE DATALYX")
    print("=" * 60)

    client = bigquery.Client(project=PROJECT_ID)

    print("\nCriando tabelas...")
    ensure_table(client, "tickets", TICKETS_SCHEMA)
    ensure_table(client, "sla_metricas", SLA_SCHEMA)

    print("\nCarregando tickets...")
    df = load_tickets(client)

    print("Gerando métricas de SLA...")
    generate_and_load_sla(client, df)

    print("\nSetup concluído!")
    print(f"  tickets:      {len(df)} registros")
    print(f"  sla_metricas: {len(df)} registros")
    print(f"  contratos:    já existia no BigQuery")


if __name__ == "__main__":
    main()
