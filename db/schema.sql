CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS articles (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  category TEXT NOT NULL,
  updated DATE NOT NULL,
  body TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
  id SERIAL PRIMARY KEY,
  article_id TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  section TEXT NOT NULL,
  content TEXT NOT NULL,
  embedding vector(768),
  tsv tsvector
);
CREATE INDEX IF NOT EXISTS chunks_tsv_idx ON chunks USING GIN (tsv);
CREATE INDEX IF NOT EXISTS chunks_embedding_idx ON chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS products (
  sku TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  price_inr INTEGER NOT NULL,
  stock INTEGER NOT NULL,
  warranty_months INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
  order_id TEXT PRIMARY KEY,
  customer_name TEXT NOT NULL,
  email TEXT NOT NULL,
  phone TEXT NOT NULL,
  total_inr INTEGER NOT NULL,
  status TEXT NOT NULL,
  ordered_at TIMESTAMPTZ NOT NULL,
  shipped_at TIMESTAMPTZ,
  delivered_at TIMESTAMPTZ,
  carrier TEXT,
  tracking TEXT
);

CREATE TABLE IF NOT EXISTS order_items (
  order_id TEXT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
  sku TEXT NOT NULL REFERENCES products(sku),
  qty INTEGER NOT NULL,
  price_inr INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS past_tickets (
  ticket_id TEXT PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL,
  subject TEXT NOT NULL,
  body TEXT NOT NULL,
  resolution TEXT
);

-- Created by the agent at runtime
CREATE TABLE IF NOT EXISTS tickets (
  id SERIAL PRIMARY KEY,
  ticket_ref TEXT UNIQUE NOT NULL,
  summary TEXT NOT NULL,
  priority TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  session_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE SEQUENCE IF NOT EXISTS ticket_ref_seq START 1001;

CREATE TABLE IF NOT EXISTS returns (
  id SERIAL PRIMARY KEY,
  order_id TEXT NOT NULL REFERENCES orders(order_id),
  skus TEXT[] NOT NULL,
  reason TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'requested',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- units per SKU when the customer returns only part of an order line (added 2026-11-09)
ALTER TABLE returns ADD COLUMN IF NOT EXISTS qty JSONB;

CREATE TABLE IF NOT EXISTS request_log (
  id SERIAL PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  session_id TEXT,
  record JSONB NOT NULL,
  latency_ms INTEGER
);
