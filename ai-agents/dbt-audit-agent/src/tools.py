import os
import json

_BASE = os.path.join(os.path.dirname(__file__), "..")
_DBT_DIR = os.path.join(_BASE, "dbt_project")
_LOGS_DIR = os.path.join(_BASE, "logs")
_SCHEMA_FILE = os.path.join(_BASE, "source_schema.json")


def ler_log(nome_arquivo: str = "error_log.txt") -> str:
    """Lê o arquivo de log de erro do dbt para identificar qual modelo falhou e qual foi o erro.

    Args:
        nome_arquivo: Nome do arquivo de log. Padrão: error_log.txt
    """
    print(f"  [tool] ler_log('{nome_arquivo}')")
    path = os.path.join(_LOGS_DIR, nome_arquivo)
    if not os.path.exists(path):
        return f"Arquivo '{nome_arquivo}' não encontrado em {_LOGS_DIR}"
    with open(path, encoding="utf-8") as f:
        return f.read()


def ler_modelo(nome_modelo: str) -> str:
    """Lê o código SQL de um modelo dbt pelo nome.

    Args:
        nome_modelo: Nome do modelo sem extensão, ex: fct_receita
    """
    print(f"  [tool] ler_modelo('{nome_modelo}')")
    for root, _, files in os.walk(_DBT_DIR):
        for f in files:
            if f == f"{nome_modelo}.sql":
                with open(os.path.join(root, f), encoding="utf-8") as file:
                    return file.read()
    return f"Modelo '{nome_modelo}' não encontrado no projeto dbt."


def listar_modelos() -> str:
    """Lista todos os modelos dbt do projeto com seus caminhos, útil para entender dependências."""
    print("  [tool] listar_modelos()")
    models = []
    for root, _, files in os.walk(_DBT_DIR):
        for f in files:
            if f.endswith(".sql"):
                rel = os.path.relpath(os.path.join(root, f), _DBT_DIR)
                models.append(rel.replace("\\", "/"))
    return "\n".join(sorted(models)) if models else "Nenhum modelo encontrado."


def verificar_schema(nome_tabela: str) -> str:
    """Verifica as colunas disponíveis em uma tabela ou modelo dbt.

    Args:
        nome_tabela: Nome da tabela ou modelo, ex: stg_pedidos ou raw.pedidos
    """
    print(f"  [tool] verificar_schema('{nome_tabela}')")
    with open(_SCHEMA_FILE, encoding="utf-8") as f:
        schema = json.load(f)
    if nome_tabela in schema:
        cols = schema[nome_tabela]
        linhas = [f"Colunas de '{nome_tabela}':"]
        for c in cols:
            nota = f"  <- {c['nota']}" if "nota" in c else ""
            linhas.append(f"  - {c['nome']} ({c['tipo']}){nota}")
        return "\n".join(linhas)
    tabelas = list(schema.keys())
    return f"Tabela '{nome_tabela}' não encontrada. Disponíveis: {tabelas}"
