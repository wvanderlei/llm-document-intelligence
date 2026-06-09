import os
import sys
import argparse

import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
import google.generativeai as genai
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from quota_tracker import track, status

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
COLLECTION_NAME = "contratos"
TOP_K = 2


class GeminiEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        embeddings = []
        for text in input:
            track()
            result = genai.embed_content(model="models/text-embedding-004", content=text)
            embeddings.append(result["embedding"])
        return embeddings


def search(collection, question: str) -> list[dict]:
    results = collection.query(query_texts=[question], n_results=TOP_K)
    chunks = []
    for i, doc in enumerate(results["documents"][0]):
        chunks.append({
            "text": doc,
            "source": results["metadatas"][0][i]["source"],
        })
    return chunks


def answer(question: str, chunks: list[dict]) -> str:
    model = genai.GenerativeModel("gemini-2.5-flash")

    context = "\n\n---\n\n".join([
        f"[Fonte: {c['source']}]\n{c['text']}"
        for c in chunks
    ])

    prompt = f"""Você é um assistente especializado em análise de contratos da Datalyx.
Use APENAS os trechos abaixo para responder. Se a informação não estiver nos trechos, diga claramente.

TRECHOS RELEVANTES:
{context}

PERGUNTA: {question}"""

    track()
    response = model.generate_content(prompt)
    return response.text


def main():
    parser = argparse.ArgumentParser(description="Chatbot RAG sobre contratos")
    parser.add_argument("--question", required=True, help="Pergunta sobre os contratos")
    args = parser.parse_args()

    client = chromadb.PersistentClient(path=CHROMA_DIR)

    collections = [c.name for c in client.list_collections()]
    if COLLECTION_NAME not in collections:
        print("Erro: documentos nao indexados. Execute primeiro: python src\\indexer.py")
        return

    status()
    embed_fn = GeminiEmbeddingFunction()
    collection = client.get_collection(name=COLLECTION_NAME, embedding_function=embed_fn)
    print(f"Base de conhecimento: {collection.count()} chunks indexados\n")

    print(f"Pergunta: {args.question}\n")
    print("Buscando trechos relevantes...")
    chunks = search(collection, args.question)

    print(f"Encontrados {len(chunks)} trecho(s). Gerando resposta...\n")
    resposta = answer(args.question, chunks)

    print("=" * 60)
    print("RESPOSTA:")
    print("=" * 60)
    print(resposta)

    print("\nFontes consultadas:")
    for c in chunks:
        print(f"  - {c['source']}")


if __name__ == "__main__":
    main()
