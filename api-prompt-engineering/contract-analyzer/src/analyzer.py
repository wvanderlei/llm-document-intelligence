import os
import sys
import argparse
import fitz  # PyMuPDF
import google.generativeai as genai
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from quota_tracker import track, status

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))


def extract_text_from_pdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(pages)


def ask_about_contract(contract_text: str, question: str) -> str:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""Você é um assistente jurídico especializado em análise de contratos.
Abaixo está o texto completo de um contrato:

--- INÍCIO DO CONTRATO ---
{contract_text}
--- FIM DO CONTRATO ---

Responda à seguinte pergunta com base exclusivamente no texto acima.
Se a informação não estiver no contrato, diga claramente que não foi encontrada.

Pergunta: {question}"""

    response = model.generate_content(prompt)
    return response.text


def main():
    parser = argparse.ArgumentParser(description="Analisador de contratos com Gemini AI")
    parser.add_argument("--file", required=True, help="Caminho para o arquivo PDF do contrato")
    parser.add_argument("--question", required=True, help="Pergunta sobre o contrato")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Erro: arquivo '{args.file}' não encontrado.")
        sys.exit(1)

    print(f"Lendo contrato: {args.file}")
    contract_text = extract_text_from_pdf(args.file)

    if not contract_text.strip():
        print("Erro: não foi possível extrair texto do PDF. Verifique se o PDF não é uma imagem escaneada.")
        sys.exit(1)

    print(f"Texto extraído: {len(contract_text)} caracteres\n")
    print(f"Pergunta: {args.question}\n")
    status()
    print("Consultando Gemini...\n")

    track()
    answer = ask_about_contract(contract_text, args.question)

    print("=" * 60)
    print("RESPOSTA:")
    print("=" * 60)
    print(answer)


if __name__ == "__main__":
    main()
