# ADR-0003 · Docker Compose for every environment

**Status:** Accepted · 2026-09-26

## Context

The stakeholder wants the Python environment, PostgreSQL and the LLM to run in Docker. The project must also start the same way on the developer's Windows laptop, a teammate's machine, CI and the demo laptop. OCR libraries and PostgreSQL extensions are painful to install natively on Windows.

## Decision

- Every service is a container in one `compose.yaml` at the repository root: `db`, `api`, `worker`, `web` and optional `ollama`.
- The Python environment is built inside the image with **uv** from a committed lockfile (`backend/uv.lock`, `uv sync --locked`). No local virtualenv is needed.
- Development uses bind mounts for source code (hot reload); images stay usable without them.
- Optional or heavy services use **Compose profiles** (`--profile local-llm`), so the default stack stays light.
- Configuration comes only from environment variables (`.env`, template in `.env.example`).
- Ports bind to `127.0.0.1`; WSL 2 memory is capped at 10 GB.

## Alternatives considered

| Option | Why not |
|---|---|
| Native installs (conda + local Postgres) | "Works on my machine" issues; PaddleOCR and pgvector setup differs per OS |
| Dev containers only | Useful later for editor integration, but Compose is still needed for multi-service runs |
| Kubernetes (kind/minikube) | Far more complexity than one machine needs |

## Consequences

- `docker compose up --build` is the single documented way to run Nabz.
- Image rebuilds are needed when dependencies change (cached by uv).
- Docker Desktop's WSL 2 VM adds memory overhead on Windows. This is handled by the memory cap and the opt-in LLM profile.
- CI can run the same images with service containers.
