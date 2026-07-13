-- Ejecuta esto en Supabase: Dashboard → SQL Editor → New query → pega y ejecuta (Run)

-- 1. Habilitar la extensión de vectores
create extension if not exists vector;

-- 2. Tabla donde se guardan los fragmentos de texto y sus embeddings
create table if not exists documents (
  id text primary key,
  content text not null,
  source text not null,
  chunk_index int not null,
  embedding vector(768)  -- debe coincidir con EMBEDDING_DIM en rag_engine.py
);

-- 3. Índice para que la búsqueda por similitud sea rápida
create index if not exists documents_embedding_idx
  on documents
  using hnsw (embedding vector_cosine_ops);

-- 4. Función que hace la búsqueda de similitud (la usa la app para recuperar contexto)
create or replace function match_documents (
  query_embedding vector(768),
  match_count int default 5
)
returns table (
  id text,
  content text,
  source text,
  similarity float
)
language sql stable
as $$
  select
    documents.id,
    documents.content,
    documents.source,
    1 - (documents.embedding <=> query_embedding) as similarity
  from documents
  order by documents.embedding <=> query_embedding
  limit match_count;
$$;
