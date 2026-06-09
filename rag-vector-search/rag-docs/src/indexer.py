import os
import sys
import glob
import argparse

import fitz  # PyMuPDF
import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
import google.generativeai as genai
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from quota_tracker import track, status

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

CONTRACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "api-prompt-engineering", "contract-analyzer", "contracts")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
COLLECTION_NAME = "contratos"
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 0


class GeminiEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        embeddings = []
        for text in input:
            track()
            result = genai.embed_content(model="models/text-embedding-004", content=text)
            embeddings.append(result["embedding"])
        return embeddings


def extract_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(pages)


def split_into_chunks(text: str, source: str) -> list[dict]:
    words = text.split()
    chunks = []
    for i, chunk_id in enumerate(range(0, len(words), CHUNK_SIZE)):
        chunk_text = " ".join(words[chunk_id: chunk_id + CHUNK_SIZE])
        chunks.append({
            "id": f"{source}__chunk_{i}",
            "text": chunk_text,
            "source": source,
            "chunk_index": i,
        })
    return chunks


def main():
    parser = argparse.ArgumentParser(description="Indexador de contratos para RAG")
    parser.add_argument("--force", action="store_true", help="Força re-indexacao mesmo se já existir")
    args = parser.parse_args()

    print("=" * 60)
    print("INDEXADOR DE CONTRATOS — RAG")
    print("=" * 60)

    status()

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    existing = [c.name for c in client.list_collections()]

    if COLLECTION_NAME in existing and not args.force:
        count = client.get_collection(COLLECTION_NAME).count()
        print(f"\nColecao '{COLLECTION_NAME}' já existe com {count} chunks.")
        print("Use --force para re-indexar e gastar requisicoes de embedding.")
        return

    pdf_files = glob.glob(os.path.join(CONTRACTS_DIR, "*.pdf"))
    if not pdf_files:
        print(f"Nenhum PDF encontrado em: {CONTRACTS_DIR}")
        return

    print(f"\n{len(pdf_files)} PDF(s) encontrado(s).")

    if COLLECTION_NAME in existing:
        client.delete_collection(COLLECTION_NAME)

    embed_fn = GeminiEmbeddingFunction()
    collection = client.create_collection(name=COLLECTION_NAME, embedding_function=embed_fn)

    all_chunks = []
    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        print(f"\nProcessando: {filename}")
        text = extract_text(pdf_path)
        chunks = split_into_chunks(text, filename)
        all_chunks.extend(chunks)
        print(f"  {len(chunks)} chunk(s) gerado(s)")

    print(f"\nTotal: {len(all_chunks)} chunks. Gerando embeddings e salvando no ChromaDB...")

    batch_size = 5
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i: i + batch_size]
        collection.add(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            metadatas=[{"source": c["source"], "chunk_index": c["chunk_index"]} for c in batch],
        )
        print(f"  Indexados {min(i + batch_size, len(all_chunks))}/{len(all_chunks)} chunks...")

    print(f"\nIndexacao concluida! {collection.count()} chunks salvos em '{CHROMA_DIR}'.")


if __name__ == "__main__":
    main()
