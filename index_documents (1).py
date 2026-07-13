"""
index_documents.py
Ejecuta esto UNA SOLA VEZ desde tu computadora (no en Streamlit Cloud) para
procesar los 5 PDFs de data/ y guardar sus embeddings en Supabase.

Uso:
    python index_documents.py

Requiere las variables de entorno (o un archivo .env):
    GEMINI_API_KEY
    SUPABASE_URL
    SUPABASE_KEY   (usa la "service_role" key, no la "anon", para poder escribir)
"""

import os
import sys
import time
import glob
import hashlib

from google import genai
from google.genai import types
from google.genai import errors as genai_errors
from pypdf import PdfReader
from supabase import create_client

# ---------- Configuración (debe coincidir con rag_engine.py) ----------
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 300
SECONDS_BETWEEN_CALLS = 0.75  # respeta el límite de 100 peticiones/min del plan gratuito


def get_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"❌ Falta la variable de entorno {name}. Expórtala antes de correr el script.")
        sys.exit(1)
    return value


def extract_text_from_pdf(path: str) -> str:
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def chunk_text(text: str, source: str, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    text = " ".join(text.split())
    chunks = []
    start, idx = 0, 0
    while start < len(text):
        chunk = text[start:start + chunk_size]
        if chunk.strip():
            chunks.append({
                "id": hashlib.md5(f"{source}-{idx}".encode()).hexdigest(),
                "content": chunk,
                "source": source,
                "chunk_index": idx,
            })
        start += chunk_size - overlap
        idx += 1
    return chunks


def embed_with_retry(client, text: str, task_type: str):
    for attempt in range(5):
        try:
            result = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=EMBEDDING_DIM,
                ),
            )
            return result.embeddings[0].values
        except genai_errors.ClientError as e:
            status = getattr(e, "status_code", getattr(e, "code", None))
            if status == 429 and attempt < 4:
                print("   ⏳ Límite de cuota alcanzado, esperando 65s...")
                time.sleep(65)
                continue
            raise
    raise RuntimeError("No se pudo generar el embedding tras varios reintentos.")


def main():
    gemini_key = get_env("GEMINI_API_KEY")
    supabase_url = get_env("SUPABASE_URL")
    supabase_key = get_env("SUPABASE_KEY")

    client = genai.Client(api_key=gemini_key)
    supabase = create_client(supabase_url, supabase_key)

    pdf_paths = sorted(glob.glob(os.path.join("data", "*.pdf")))
    if not pdf_paths:
        print("❌ No se encontraron PDFs en la carpeta 'data/'.")
        sys.exit(1)

    print(f"📄 Encontrados {len(pdf_paths)} PDFs: {[os.path.basename(p) for p in pdf_paths]}")

    all_chunks = []
    for path in pdf_paths:
        text = extract_text_from_pdf(path)
        source_name = os.path.basename(path)
        chunks = chunk_text(text, source_name)
        print(f"   {source_name}: {len(chunks)} fragmentos")
        all_chunks.extend(chunks)

    print(f"\n🔢 Generando embeddings para {len(all_chunks)} fragmentos (esto puede tardar varios minutos)...")

    for i, chunk in enumerate(all_chunks):
        embedding = embed_with_retry(client, chunk["content"], task_type="RETRIEVAL_DOCUMENT")
        supabase.table("documents").upsert({
            "id": chunk["id"],
            "content": chunk["content"],
            "source": chunk["source"],
            "chunk_index": chunk["chunk_index"],
            "embedding": embedding,
        }).execute()
        print(f"   [{i + 1}/{len(all_chunks)}] {chunk['source']} (chunk {chunk['chunk_index']}) ✅")
        time.sleep(SECONDS_BETWEEN_CALLS)

    print(f"\n✅ Listo. {len(all_chunks)} fragmentos indexados en Supabase.")


if __name__ == "__main__":
    main()
