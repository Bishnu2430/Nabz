# ADR-0002 · PostgreSQL as the single datastore

**Status:** Accepted · 2026-09-26

## Context

Nabz needs:

- relational records (users, reports, observations)
- a durable job queue for slow OCR and LLM work
- fuzzy search over test aliases
- vector search over about 3,000 knowledge passages

The stakeholder asked for PostgreSQL and no SQLite. One developer has to run and understand everything on a 16 GB laptop.

## Decision

Use **PostgreSQL 17** (image `pgvector/pgvector:pg17`) for all of it:

- **Records.** Normal tables, managed by Alembic migrations.
- **Queue.** A `processing_job` table claimed with `SELECT … FOR UPDATE SKIP LOCKED`. Retries use `run_after` back-off, and status events use `LISTEN/NOTIFY`.
- **Fuzzy matching.** `pg_trgm` GIN index on `lab_test.aliases`.
- **Vectors.** `pgvector` `vector(384)` with an HNSW index (cosine).
- **Field encryption and UUIDs.** `pgcrypto`.

## Alternatives considered

| Option | Why not |
|---|---|
| SQLite | Excluded by the stakeholder; weak concurrency for API + worker |
| Postgres + Redis/Celery for jobs | One more service to run and secure; the transactional coupling of job and report state would be lost |
| Postgres + a vector DB (Qdrant, Chroma) | Another container and consistency problem, for a corpus small enough for pgvector |
| MongoDB | Relational integrity (profiles → reports → observations) matters more than schema flexibility |

## Consequences

- One backup, one connection pool, one place to look when debugging.
- Job enqueue and report status change happen in the **same transaction**, so no lost or orphan jobs.
- Throughput is bounded by Postgres. That is far above the needs of a demo (tens of reports per hour). If Nabz ever needs thousands of jobs per second, revisit with a dedicated broker.
- Host port 5433 avoids a clash with the locally installed PostgreSQL 18.
