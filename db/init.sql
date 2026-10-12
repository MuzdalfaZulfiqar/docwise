CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text UNIQUE NOT NULL,
  password_hash text NOT NULL,
  daily_token_quota int NOT NULL DEFAULT 200000,
  max_documents int NOT NULL DEFAULT 50,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS documents (
  id uuid PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  filename text NOT NULL,
  storage_path text NOT NULL,
  size_bytes bigint NOT NULL DEFAULT 0,
  status text NOT NULL DEFAULT 'queued',  -- queued | parsing | embedding | ready | failed
  progress int NOT NULL DEFAULT 0,
  error text,
  pages int,
  chunk_count int,
  chunk_strategy text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS documents_user_idx ON documents(user_id);

-- user_id is denormalised onto chunks so EVERY retrieval query can filter on it directly.
CREATE TABLE IF NOT EXISTS chunks (
  id bigserial PRIMARY KEY,
  document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  idx int NOT NULL,
  text text NOT NULL,
  page int NOT NULL,
  char_start int NOT NULL,
  char_end int NOT NULL,
  heading text,
  embedding vector(1536) NOT NULL,
  tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED
);
CREATE INDEX IF NOT EXISTS chunks_user_idx ON chunks(user_id);
CREATE INDEX IF NOT EXISTS chunks_doc_idx ON chunks(document_id, idx);
CREATE INDEX IF NOT EXISTS chunks_tsv_idx ON chunks USING gin(tsv);
CREATE INDEX IF NOT EXISTS chunks_emb_idx ON chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS embedding_cache (
  hash text PRIMARY KEY,
  embedding vector(1536) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS conversations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title text NOT NULL DEFAULT 'New chat',
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS conversations_user_idx ON conversations(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS messages (
  id bigserial PRIMARY KEY,
  conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role text NOT NULL,                 -- user | assistant
  content text NOT NULL,
  sources jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS messages_conv_idx ON messages(conversation_id, id);

CREATE TABLE IF NOT EXISTS usage_log (
  id bigserial PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind text NOT NULL,                 -- chat | embed_ingest
  model text,
  input_tokens int NOT NULL DEFAULT 0,
  output_tokens int NOT NULL DEFAULT 0,
  embed_tokens int NOT NULL DEFAULT 0,
  cost_usd numeric(12,6) NOT NULL DEFAULT 0,
  latency_ms int,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS usage_user_time_idx ON usage_log(user_id, created_at);
