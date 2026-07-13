"""
rag_engine.py
Lógica de consulta del RAG: recibe una pregunta, la convierte en embedding,
busca los fragmentos más similares en Supabase (pgvector) y genera la
respuesta con Gemini.
"""

from typing import List, Dict

from google import genai
from google.genai import types
from supabase import Client

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768          # debe coincidir con supabase_setup.sql e index_documents.py
GENERATION_MODEL = "gemini-3.5-flash"
TOP_K = 5


def get_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def embed_query(client: genai.Client, question: str) -> List[float]:
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=question,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=EMBEDDING_DIM,
        ),
    )
    return result.embeddings[0].values


def search_documents(supabase: Client, query_embedding: List[float], top_k: int = TOP_K) -> List[Dict]:
    response = supabase.rpc(
        "match_documents",
        {"query_embedding": query_embedding, "match_count": top_k},
    ).execute()
    return response.data or []


def answer_question(client: genai.Client, supabase: Client, question: str) -> Dict:
    query_embedding = embed_query(client, question)
    matches = search_documents(supabase, query_embedding)

    if not matches:
        return {
            "answer": "No encontré información relevante en los documentos para responder eso.",
            "sources": [],
        }

    context = "\n\n---\n\n".join(
        f"[Fuente: {m['source']}]\n{m['content']}" for m in matches
    )

    system_prompt = (
        "Eres un asistente que responde preguntas basándose ÚNICAMENTE en el contexto "
        "proporcionado, extraído de documentos PDF. Si la respuesta no está en el contexto, "
        "dilo claramente en vez de inventar información. Responde en español, de forma clara "
        "y cita la fuente (nombre del documento) cuando sea relevante."
    )

    prompt = f"Contexto:\n{context}\n\nPregunta: {question}\n\nRespuesta:"

    response = client.models.generate_content(
        model=GENERATION_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.2,
        ),
    )

    sources = sorted(set(m["source"] for m in matches))

    return {
        "answer": response.text,
        "sources": sources,
    }


def count_documents(supabase: Client) -> int:
    response = supabase.table("documents").select("id", count="exact").limit(1).execute()
    return response.count or 0
