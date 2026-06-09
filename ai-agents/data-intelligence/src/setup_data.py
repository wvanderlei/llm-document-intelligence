import os
import random
from datetime import date, datetime, timedelta

import pandas as pd
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".env"))

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
DATASET_ID = "datalyx_analytics"

# ── Schemas ───────────────────────────────────────────────────────────────────

CONTRATOS_SCHEMA = [
    bigquery.SchemaField("cliente",      "STRING"),
    bigquery.SchemaField("modelo",       "STRING"),   # Radar / Forja / Nexus
    bigquery.SchemaField("tipo",         "STRING"),   # recorrente / pontual
    bigquery.SchemaField("valor_mensal", "FLOAT"),
    bigquery.SchemaField("status",       "STRING"),
    bigquery.SchemaField("data_inicio",  "DATE"),
    bigquery.SchemaField("horas_pacote", "INTEGER"),  # apenas Nexus: 40 / 80 / 120
]

TICKETS_SCHEMA = [
    bigquery.SchemaField("id",           "STRING"),
    bigquery.SchemaField("texto",        "STRING"),
    bigquery.SchemaField("categoria",    "STRING"),
    bigquery.SchemaField("prioridade",   "STRING"),
    bigquery.SchemaField("cliente",      "STRING"),
    bigquery.SchemaField("modelo",       "STRING"),
    bigquery.SchemaField("data_abertura","DATE"),
]

SLA_SCHEMA = [
    bigquery.SchemaField("ticket_id",             "STRING"),
    bigquery.SchemaField("cliente",               "STRING"),
    bigquery.SchemaField("modelo",                "STRING"),
    bigquery.SchemaField("categoria",             "STRING"),
    bigquery.SchemaField("tempo_resposta_horas",  "FLOAT"),
    bigquery.SchemaField("resolvido",             "BOOL"),
    bigquery.SchemaField("data_resolucao",        "DATE"),
]

# ── Clientes ──────────────────────────────────────────────────────────────────
# perfil: saudavel | em_risco | critico | novo | churning | fidelizado

CLIENTES = [
    # cliente,       modelo,  tipo,        valor,    horas, status,  data_inicio,   perfil,      ticket_vol
    ("DataCorp",    "Nexus",  "recorrente", 22000.0,  80,   "ativo", "2023-06-01",  "saudavel",   60),
    ("TechBrasil",  "Forja",  "pontual",    55000.0,   0,   "ativo", "2024-01-10",  "saudavel",   30),
    ("Varejo360",   "Nexus",  "recorrente", 12000.0,  40,   "ativo", "2023-11-01",  "em_risco",   55),
    ("FinanSol",    "Radar",  "pontual",     9500.0,   0,   "ativo", "2024-09-15",  "novo",       15),
    ("LogiData",    "Forja",  "pontual",    72000.0,   0,   "ativo", "2024-03-20",  "saudavel",   35),
    ("RetailMax",   "Nexus",  "recorrente", 12000.0,  40,   "ativo", "2023-08-01",  "churning",   20),
    ("AgriTech",    "Radar",  "pontual",     8000.0,   0,   "ativo", "2024-10-01",  "novo",       10),
    ("MediFlow",    "Nexus",  "recorrente", 32000.0, 120,   "ativo", "2023-04-01",  "critico",    70),
    ("EduData",     "Forja",  "pontual",    38000.0,   0,   "ativo", "2024-05-10",  "saudavel",   25),
    ("IndustriaX",  "Nexus",  "recorrente", 22000.0,  80,   "ativo", "2023-02-01",  "fidelizado", 50),
]

# ── Templates de tickets por perfil ───────────────────────────────────────────

TEMPLATES = {
    "critico": {
        "incidente": [
            "pipeline principal parou durante a madrugada, dados críticos indisponíveis",
            "tabela de produção com valores zerados desde ontem, impacto nos relatórios",
            "erro crítico na carga noturna, zero registros inseridos",
            "falha grave no pipeline de integração, sistema de origem sem resposta",
            "dados inconsistentes na tabela principal, auditoria bloqueada",
            "job de transformação falhou com erro de schema, pipeline parado",
            "dashboard executivo fora do ar, reunião de board amanhã",
            "carga de dados atrasada 8 horas, equipe operacional sem informação",
        ],
        "duvida": [
            "como verificar se os dados estão atualizados corretamente?",
            "qual o procedimento em caso de falha recorrente?",
        ],
        "manutencao": [
            "ajustar threshold de alerta para incidentes críticos",
            "revisar regras de validação que estão gerando falsos positivos",
        ],
        "fora_de_escopo": [
            "precisamos de um novo módulo de compliance urgente",
        ],
    },
    "em_risco": {
        "incidente": [
            "pipeline atrasou 3 horas sem alertas automáticos",
            "relatório semanal chegou com dados duplicados",
            "filtro de data no dashboard não está funcionando",
        ],
        "duvida": [
            "como interpretar o campo status_pedido na tabela de vendas?",
            "qual a frequência de atualização dos dados?",
            "onde consigo o histórico de cargas anteriores?",
        ],
        "manutencao": [
            "adicionar nova filial no filtro do dashboard de vendas",
            "mudar horário do relatório automático de segunda para terça",
            "incluir campo de margem bruta no relatório de performance",
        ],
        "fora_de_escopo": [
            "gostaríamos de integrar dados do marketplace externo",
            "precisamos de um dashboard novo para o time de marketing",
            "há possibilidade de criar análise preditiva de demanda?",
            "queremos incluir dados de redes sociais nas análises",
            "interesse em automação do processo de proposta comercial",
        ],
    },
    "churning": {
        "duvida": [
            "como exportar os dados do dashboard para Excel?",
            "qual o limite de registros no export?",
            "como faço para compartilhar o relatório com um colega?",
            "o que significa o indicador de cobertura no painel?",
            "como funciona o cálculo de margem apresentado?",
        ],
        "manutencao": [
            "corrigir título do gráfico de vendas com erro de digitação",
            "mudar cor do indicador de alerta",
            "ajustar alinhamento das colunas no export",
        ],
        "incidente": [
            "relatório não chegou por email hoje",
            "export gerando arquivo corrompido",
        ],
        "fora_de_escopo": [
            "gostaríamos de criar dashboards para outras áreas",
        ],
    },
    "saudavel": {
        "incidente": [
            "pipeline atrasou levemente esta manhã",
            "algumas linhas com valor nulo no campo CEP",
            "dashboard demorando mais que o habitual para carregar",
        ],
        "duvida": [
            "qual a granularidade dos dados de vendas, diária ou horária?",
            "como filtrar apenas pedidos de uma filial específica?",
            "o relatório de faturamento inclui notas canceladas?",
            "como funciona a regra de cálculo de comissão?",
            "posso acessar os dados diretamente pelo BigQuery?",
        ],
        "manutencao": [
            "adicionar visão por semana no gráfico que hoje só tem mês",
            "incluir CNPJ no relatório de fornecedores",
            "atualizar cálculo de meta com valores do novo trimestre",
            "adicionar filtro por vendedor no dashboard de performance",
        ],
        "fora_de_escopo": [
            "há possibilidade de expandir o escopo para incluir mais regiões?",
            "pensando em contratar um projeto adicional de previsão de demanda",
        ],
    },
    "fidelizado": {
        "incidente": [
            "alerta de anomalia disparou mas os dados parecem corretos",
            "timeout na query do painel de KPIs executivos",
        ],
        "duvida": [
            "como interpretar o novo indicador adicionado no mês passado?",
            "qual o roadmap para os próximos releases?",
        ],
        "manutencao": [
            "ajustar threshold de alerta após mudança na política comercial",
            "incluir novos campos conforme solicitado pelo financeiro",
            "otimizar query do dashboard de RH que está lenta",
            "atualizar lógica de categorização após reestruturação",
        ],
        "fora_de_escopo": [
            "interesse em ampliar o pacote de horas no próximo trimestre",
            "pensando em novo projeto de migração para BigQuery",
        ],
    },
    "novo": {
        "duvida": [
            "como acessar o dashboard pela primeira vez?",
            "quais os dados disponíveis no ambiente?",
            "como interpretar o relatório de diagnóstico entregue?",
            "qual o próximo passo após o diagnóstico?",
            "como funciona o processo de onboarding?",
        ],
        "incidente": [
            "acesso ao ambiente não está funcionando",
        ],
        "manutencao": [
            "ajustar permissões de acesso para novo colaborador",
        ],
        "fora_de_escopo": [
            "gostaríamos de contratar o próximo passo após o diagnóstico",
        ],
    },
}

PRIORIDADE_MAP = {
    "incidente":      ["alta", "alta", "alta", "media", "media"],
    "duvida":         ["baixa", "baixa", "baixa", "media"],
    "manutencao":     ["media", "media", "baixa", "baixa"],
    "fora_de_escopo": ["baixa", "baixa", "media"],
}

RESPONSE_HOURS = {
    ("incidente", "alta"):       (1, 5),
    ("incidente", "media"):      (4, 14),
    ("duvida",    "baixa"):      (12, 48),
    ("duvida",    "media"):      (8, 24),
    ("manutencao","media"):      (24, 72),
    ("manutencao","baixa"):      (48, 120),
    ("fora_de_escopo","baixa"):  (24, 96),
    ("fora_de_escopo","media"):  (12, 48),
}


def ensure_dataset(client):
    ds = bigquery.Dataset(f"{PROJECT_ID}.{DATASET_ID}")
    ds.location = "US"
    try:
        client.create_dataset(ds)
        print(f"  Dataset '{DATASET_ID}' criado.")
    except Exception:
        print(f"  Dataset '{DATASET_ID}' já existe.")


def recreate_table(client, table_id, schema):
    ref = f"{PROJECT_ID}.{DATASET_ID}.{table_id}"
    try:
        client.delete_table(ref)
    except Exception:
        pass
    client.create_table(bigquery.Table(ref, schema=schema))
    print(f"  Tabela '{table_id}' recriada.")


def load_table(client, table_id, schema, rows):
    ref = f"{PROJECT_ID}.{DATASET_ID}.{table_id}"
    job = client.load_table_from_json(
        rows, ref,
        job_config=bigquery.LoadJobConfig(
            schema=schema,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        ),
    )
    job.result()
    print(f"  {len(rows)} registros carregados em '{table_id}'.")


def build_contratos():
    rows = []
    for cliente, modelo, tipo, valor, horas, status, data_inicio, perfil, _ in CLIENTES:
        rows.append({
            "cliente":      cliente,
            "modelo":       modelo,
            "tipo":         tipo,
            "valor_mensal": valor,
            "status":       status,
            "data_inicio":  data_inicio,
            "horas_pacote": horas,
        })
    return rows


def build_tickets_and_sla():
    random.seed(42)
    today = date.today()
    ticket_rows = []
    sla_rows = []
    ticket_num = 1

    for cliente, modelo, _, _, _, _, data_inicio_str, perfil, vol in CLIENTES:
        data_inicio = date.fromisoformat(data_inicio_str)
        days_active = (today - data_inicio).days
        if days_active < 1:
            days_active = 1

        templates = TEMPLATES.get(perfil, TEMPLATES["saudavel"])

        # Distribuição de categorias por perfil
        cat_dist = {
            "critico":    ["incidente"] * 6 + ["duvida"] * 1 + ["manutencao"] * 2 + ["fora_de_escopo"] * 1,
            "em_risco":   ["incidente"] * 2 + ["duvida"] * 3 + ["manutencao"] * 3 + ["fora_de_escopo"] * 5,
            "churning":   ["incidente"] * 1 + ["duvida"] * 5 + ["manutencao"] * 3 + ["fora_de_escopo"] * 1,
            "saudavel":   ["incidente"] * 2 + ["duvida"] * 4 + ["manutencao"] * 4 + ["fora_de_escopo"] * 1,
            "fidelizado": ["incidente"] * 1 + ["duvida"] * 2 + ["manutencao"] * 6 + ["fora_de_escopo"] * 1,
            "novo":       ["incidente"] * 1 + ["duvida"] * 5 + ["manutencao"] * 1 + ["fora_de_escopo"] * 1,
        }

        for _ in range(vol):
            categoria = random.choice(cat_dist.get(perfil, cat_dist["saudavel"]))
            textos = templates.get(categoria, ["solicitação de suporte"])
            texto = random.choice(textos)
            prioridade = random.choice(PRIORIDADE_MAP[categoria])
            data_abertura = today - timedelta(days=random.randint(0, min(days_active, 365)))

            tid = f"TKT-{ticket_num:04d}"
            ticket_rows.append({
                "id":           tid,
                "texto":        texto,
                "categoria":    categoria,
                "prioridade":   prioridade,
                "cliente":      cliente,
                "modelo":       modelo,
                "data_abertura": str(data_abertura),
            })

            min_h, max_h = RESPONSE_HOURS.get((categoria, prioridade), (24, 72))
            tempo = round(random.uniform(min_h, max_h), 1)

            # Clientes críticos têm SLA mais estourado
            if perfil == "critico":
                tempo = round(tempo * random.uniform(1.5, 3.0), 1)

            resolvido = categoria != "fora_de_escopo" or random.random() < 0.15
            if resolvido:
                dt_res = datetime(data_abertura.year, data_abertura.month, data_abertura.day) + timedelta(hours=tempo + random.uniform(1, 24))
                data_res = str(min(dt_res.date(), today))
            else:
                data_res = None

            sla_rows.append({
                "ticket_id":            tid,
                "cliente":              cliente,
                "modelo":               modelo,
                "categoria":            categoria,
                "tempo_resposta_horas": tempo,
                "resolvido":            resolvido,
                "data_resolucao":       data_res,
            })

            ticket_num += 1

    return ticket_rows, sla_rows


def main():
    print("=" * 60)
    print("SETUP — DATA INTELLIGENCE DATALYX (v2)")
    print("=" * 60)

    client = bigquery.Client(project=PROJECT_ID)

    print("\nPreparando dataset e tabelas...")
    ensure_dataset(client)
    recreate_table(client, "contratos",   CONTRATOS_SCHEMA)
    recreate_table(client, "tickets",     TICKETS_SCHEMA)
    recreate_table(client, "sla_metricas", SLA_SCHEMA)

    print("\nCarregando contratos...")
    contratos = build_contratos()
    load_table(client, "contratos", CONTRATOS_SCHEMA, contratos)

    print("Gerando e carregando tickets e SLA...")
    tickets, sla = build_tickets_and_sla()
    load_table(client, "tickets",     TICKETS_SCHEMA, tickets)
    load_table(client, "sla_metricas", SLA_SCHEMA,    sla)

    print(f"\nSetup concluído!")
    print(f"  Clientes : {len(contratos)}")
    print(f"  Tickets  : {len(tickets)}")
    print(f"  SLA      : {len(sla)}")

    print("\nPerfis dos clientes:")
    for c in CLIENTES:
        print(f"  {c[0]:<12} modelo={c[1]:<6} perfil={c[7]:<12} tickets={c[8]}")


if __name__ == "__main__":
    main()
