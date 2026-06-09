import os
import re
import sys
import time

import google.generativeai as genai
import google.generativeai.protos as protos
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from quota_tracker import track, status

from tools import ler_log, ler_modelo, listar_modelos, verificar_schema

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

TOOL_FUNCTIONS = {
    "ler_log": ler_log,
    "ler_modelo": ler_modelo,
    "listar_modelos": listar_modelos,
    "verificar_schema": verificar_schema,
}

SYSTEM_PROMPT = """Você é um agente especializado em auditoria de pipelines dbt.

Quando acionado, siga este processo:
1. Leia o log de erro para identificar qual modelo falhou e qual foi o erro
2. Leia o SQL do modelo com falha
3. Verifique o schema das tabelas referenciadas para confirmar o problema
4. Liste outros modelos se precisar entender dependências

Ao final, entregue:
- DIAGNÓSTICO: causa raiz do erro em linguagem clara
- SOLUÇÃO: o SQL corrigido completo e pronto para aplicar
- IMPACTO: quais outros modelos podem ser afetados

Seja direto e técnico."""

def _call_with_retry(fn, *args, **kwargs):
    while True:
        try:
            track()
            return fn(*args, **kwargs)
        except Exception as e:
            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                match = re.search(r"retry in (\d+\.?\d*)s", str(e))
                wait = float(match.group(1)) + 2 if match else 65
                print(f"  rate limit atingido. aguardando {wait:.0f}s...")
                time.sleep(wait)
            else:
                raise


def run(initial_message: str) -> str:
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        tools=[ler_log, ler_modelo, listar_modelos, verificar_schema],
        system_instruction=SYSTEM_PROMPT,
    )
    chat = model.start_chat(enable_automatic_function_calling=False)

    response = _call_with_retry(chat.send_message, initial_message)

    while True:
        function_calls = [
            p for p in response.parts
            if hasattr(p, "function_call") and p.function_call.name
        ]

        if not function_calls:
            return response.text

        results = []
        for part in function_calls:
            fc = part.function_call
            func_args = dict(fc.args)
            result = TOOL_FUNCTIONS[fc.name](**func_args)
            results.append(protos.Part(
                function_response=protos.FunctionResponse(
                    name=fc.name,
                    response={"result": result},
                )
            ))

        response = _call_with_retry(
            chat.send_message,
            protos.Content(parts=results, role="tool")
        )


def main():
    print("=" * 60)
    print("AGENTE DE AUDITORIA DBT — DATALYX")
    print("=" * 60)
    status()
    print("\nIniciando analise do pipeline...\n")

    resultado = run(
        "O pipeline dbt falhou. Analise o log de erro, identifique o problema e entregue o diagnóstico com a correção."
    )

    print("\n" + "=" * 60)
    print("RESULTADO DA ANALISE:")
    print("=" * 60)
    print(resultado)


if __name__ == "__main__":
    main()
