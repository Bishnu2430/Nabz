# Nabz

**See what your lab report is telling you.**

Nabz reads a photo or PDF of a blood-test report and asks you to confirm the values. It then explains them in plain English, Hindi or Odia, maps them onto an interactive 3D body, and tracks how they change across years. It helps you understand your results and prepare for your doctor. It does not diagnose.

![System architecture](docs/diagrams/architecture.svg)

## Status

Sprint 3 is done: you can upload a report in the web app, watch it being read, check every value against the page image, and confirm it. See the [project plan](docs/07-project-plan.md) (1 Aug – 30 Sep 2026).

| Component | State |
|---|---|
| PostgreSQL 17 + pgvector | ✅ running in Docker |
| API (FastAPI) | ✅ profiles, upload, review and confirm (Sprint 3) |
| Database schema (22 tables, Alembic) | ✅ Sprint 1 |
| Test catalogue (70 tests) + synthetic report generator | ✅ Sprint 1 |
| Worker + job queue, PDF/OCR extraction and row parser | ✅ Sprint 2 |
| Catalogue matching, unit normalisation, row-confidence model | ✅ Sprint 3 |
| Web app: family, upload with live progress, review and confirm | ✅ Sprint 3 |
| Analysis (status, trends, change significance); explanations and narration | Sprints 4–5 |
| 3D body map; sign-in and roles | Sprints 5–6 |

## Quick start

Requirements: Docker Desktop (Compose v2). No local Python or Node needed.

```bash
cp .env.example .env
```

Set `POSTGRES_PASSWORD` in `.env` (and `GROQ_API_KEY` and `ELEVENLABS_API_KEY` once explanations and narration land), then start the stack:

```bash
docker compose up --build -d
```

```bash
curl http://localhost:8000/health/ready
```

Create the schema, load the test catalogue and run the tests:

```bash
docker compose exec api alembic upgrade head
```

```bash
docker compose exec api python -m app.cli seed-catalogue
```

```bash
docker compose exec api pytest
```

Open the web app at <http://localhost:5173>. Add a person, upload a PDF or photo of a report (samples are in `data/synthetic/samples/`), and check the values. Until sign-in arrives in Sprint 6, the development stack uses one local account (`DEV_AUTH=true`, allowed only when `APP_ENV=development`).

Frontend checks run in the `web` container:

```bash
docker compose exec web npm run typecheck
```

```bash
docker compose exec web npm test
```

Queue a report file from the command line and look at what was extracted:

```bash
docker compose exec api python -m app.cli ingest /srv/data/synthetic/samples/syn-2026-0001.pdf
```

```bash
docker compose exec api python -m app.cli show-report <report-id>
```

Measure extraction, mapping and canonical-value accuracy against synthetic ground truth (`--mode text`, `ocr` or `photo`):

```bash
docker compose exec api python -m tools.eval.extraction --mode photo --limit 10
```

Retrain the row-confidence model (reads cached extractions from `data/synthetic/train` and `eval`, writes `data/models/confidence-v1.json`):

```bash
docker compose exec worker python -m tools.train.confidence
```

On Git Bash for Windows, prefix `docker compose exec` commands that contain absolute container paths with `MSYS_NO_PATHCONV=1`.

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
frontend/    React + TypeScript web app (Vite, Tailwind, TanStack Query, i18next)
infra/       database initialisation
data/        test catalogue, synthetic reports, trained model coefficients
docs/        documentation and diagram sources
compose.yaml all services
```

## Disclaimer

Nabz is an academic prototype for education and information. It is not a medical device and does not provide medical advice, diagnosis or treatment. Always consult a qualified doctor about your results.
