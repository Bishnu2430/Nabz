-- Runs once, when the Postgres data volume is first created.
-- Schema objects are owned by Alembic migrations; this file only enables extensions.
CREATE EXTENSION IF NOT EXISTS vector;    -- pgvector: knowledge-base embeddings
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- fuzzy matching of lab-test aliases
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid(), field encryption
CREATE EXTENSION IF NOT EXISTS citext;    -- case-insensitive emails
