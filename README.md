# Nabz

**See what your lab report is telling you.**

Nabz reads a photo or PDF of a blood-test report and asks you to confirm the values. It then explains them in plain English, Hindi or Odia, maps them onto an interactive 3D body, and tracks how they change across years. It helps you understand your results and prepare for your doctor. It does not diagnose.

![System architecture](docs/diagrams/architecture.svg)

## Status

Documentation baseline and platform scaffold are in place. See the [project plan](docs/07-project-plan.md) (1 Aug – 30 Sep 2026).

| Component | State |
|---|---|
| PostgreSQL 17 + pgvector | ✅ running in Docker |
| API (FastAPI) | ✅ health endpoints |
| Worker, extraction, analysis, explanation | Sprints 2–5 |
| Web app + 3D body map | Sprints 3–6 |

## Quick start

Requirements: Docker Desktop (Compose v2). No local Python or Node needed.

```bash
cp .env.example .env
```

Set `POSTGRES_PASSWORD` (and `ANTHROPIC_API_KEY` once explanations land) in `.env`, then start the stack:

```bash
docker compose up --build -d
```

```bash
curl http://localhost:8000/health/ready
```

The optional local small LLM (row structuring) starts with:

```bash
docker compose --profile local-llm up -d
```

## Documentation

Everything lives in [`docs/`](docs/README.md): charter, requirements, architecture, data design, workflows, detailed design, project plan with Gantt chart, risk register, data sources and licensing, safety and privacy, test plan, and architecture decision records.

Diagrams are generated from source. To rebuild them:

```bash
python docs/diagrams/src/build.py
```

## Repository layout

```text
backend/     FastAPI API and worker (Python 3.12, uv)
frontend/    React + three.js web app (Sprint 3)
infra/       database initialisation
docs/        documentation and diagram sources
compose.yaml all services
```

## Disclaimer

Nabz is an academic prototype for education and information. It is not a medical device and does not provide medical advice, diagnosis or treatment. Always consult a qualified doctor about your results.
