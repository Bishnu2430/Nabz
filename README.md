# Nabz

**See what your lab report is telling you.**

Nabz reads a photo or PDF of a blood-test report and asks you to confirm the values. It then explains them in plain English, Hindi or Odia, maps them onto an interactive 3D body, and tracks how they change across years. It helps you understand your results and prepare for your doctor. It does not diagnose.

![System architecture](docs/diagrams/architecture.svg)

## Status

Sprint 6 is done: accounts with two-step sign-in for staff; data export and deletion; and a 3D body map whose organ panels give each result's exact value, range and history. Since then:
- other records (X-ray and scan reports with an image viewer, prescriptions);
- a printable summary for the doctor;
- report comparison and search across all tests;
- a sample family, the Mohantys, with five years of reports;
- story mode, which replays a person's reports with the turning points in words;
- share links for a doctor, with a QR code;
- reminders, home readings and a printable emergency card;
- a first-run walkthrough with a sample report;
- questions about a report, with fixed replies to anything diagnostic ([ADR-0013](docs/adr/0013-rules-first-questions.md));
- a safety review for clinical reviewers and system pages for staff;
- the whole interface in Hindi and Odia;
- a parent or guardian's consent for a child, and editing a person's details;
- an offline mode for the demonstration, with a rehearsal;
- doctors on Nabz: a verified clinician reads the reports a family shares and leaves notes;
- the catalogue and the knowledge base edited on the console, with critical-limit changes approved by a clinical reviewer;
- terms of use, an about page with every source and licence, and help, in three languages;
- an OWASP ASVS 5.0 Level 1 self-assessment ([docs/13](docs/13-security-assessment.md)): six findings fixed; what is left needs HTTPS in front of the demonstration.

See the [project plan](docs/07-project-plan.md) (1 Aug – 30 Sep 2026).

| Component | State |
|---|---|
| PostgreSQL 17 + pgvector | ✅ running in Docker |
| API (FastAPI) | ✅ profiles, upload, review and confirm (Sprint 3) |
| Database schema (22 tables, Alembic) | ✅ Sprint 1 |
| Test catalogue (70 tests) + synthetic report generator | ✅ Sprint 1 |
| Worker + job queue, PDF/OCR extraction and row parser | ✅ Sprint 2 |
| Catalogue matching, unit normalisation, row-confidence model | ✅ Sprint 3 |
| Web app: family, upload with live progress, review and confirm | ✅ Sprint 3 |
| Analysis: status, critical values, change significance (RCV), trends, NHANES percentiles | ✅ Sprint 4 |
| Explanations (Groq gpt-oss-120b, MedlinePlus retrieval, validator + judge, template fallback) and narration (ElevenLabs) | ✅ Sprint 5 |
| Accounts, sessions, two-step sign-in; export and deletion; 3D body map with organ panels and timeline | ✅ Sprint 6 |
| Other records with an imaging viewer; doctor summary; compare; all tests; sample family | ✅ after Sprint 6 |
| Story mode; sharing; reminders, home readings, emergency card; walkthrough; questions; safety review and system pages; full Hindi and Odia | ✅ after Sprint 6 |
| Guardians; offline mode; doctors on Nabz; catalogue and knowledge administration; terms, about and help; security hardening | ✅ finishing the requirements |

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

Open the web app at <http://localhost:5173> and create an account. Every email (the confirmation link, password resets) lands in the Mailpit inbox at <http://localhost:8025>; nothing is sent to real addresses. Then add a person, upload a PDF or photo of a report (samples are in `data/synthetic/samples/`), check the values and open the results with the body map.

Staff accounts for the safety review (`/review`) and system pages (`/admin`) are quickest with `tools.staff`. It confirms the account, turns on two-step sign-in and prints a new password and authenticator key once (add the key, or the `otpauth://` link, to an authenticator app):

```bash
docker compose exec api python -m tools.staff --email reviewer@nabz.local --role reviewer
```

```bash
docker compose exec api python -m tools.staff --email admin@nabz.local --role admin
```

A doctor's account works the same way, with their registration; `--verified` marks it as checked, as an admin does on the console's Doctors tab. Use an invented name and number:

```bash
docker compose exec api python -m tools.staff --email doctor@nabz.local --role clinician --name "Dr. Anjali Rath" --registration "OCMR 40213" --council "Odisha Council of Medical Registration" --specialty "General medicine" --verified
```

Or create any account from the command line (reviewers and admins must then turn on two-step sign-in in Settings):

```bash
docker compose exec api python -m app.cli create-user --email reviewer@nabz.local --password "<password>" --role reviewer
```

Load the sample family into an account: five people, 38 lab reports and 5 X-ray and MRI reports from 2021 to 2026, uploaded and confirmed through the API as a person would. It also writes their emergency cards, reminders and home readings, dated from the day it runs. `--replace` first deletes everyone on that account; without it, people already there keep their reports and get fresh care data:

```bash
docker compose exec api python -m tools.family --email dev@nabz.local --replace
```

The development account is `dev@nabz.local`. Choose a password for it (keep it in your own `.env` as `DEV_ACCOUNT_PASSWORD`, never in `.env.example`) and set it:

```bash
docker compose exec api python -m app.cli set-password --email dev@nabz.local --password "<DEV_ACCOUNT_PASSWORD>"
```

Outside development, set `SECRET_KEY` (32+ characters; the API refuses to start without it) and `COOKIE_SECURE=true` behind HTTPS.

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

Measure trend detection on synthetic histories with a planted drift:

```bash
docker compose exec api python -m tools.synthetic --count 0 --histories 50 --visits 5 --seed 21 --out /srv/data/synthetic/histories
```

```bash
docker compose exec api python -m tools.eval.trends --dir /srv/data/synthetic/histories
```

Rebuild the population percentiles from NHANES (sources and checksums in [`data/external.md`](data/external.md)):

```bash
docker compose exec api python -m tools.nhanes fetch
```

```bash
docker compose exec api python -m tools.nhanes build
```

Build the knowledge base for explanations (MedlinePlus Connect → passages → embeddings; sources and checksums in [`data/external.md`](data/external.md)). The passages are committed, so after a fresh clone only the embedding model and the last command are needed:

```bash
docker compose exec api python -m tools.knowledge fetch
```

```bash
docker compose exec api python -m tools.knowledge build
```

```bash
docker compose exec api python -m app.cli load-knowledge
```

Evaluate explanations and Ask Nabz live against Groq (uses your `GROQ_API_KEY`; each takes about 25 minutes on the free tier, whose 200,000 tokens a day cover roughly one of them). Both run in a transaction that is rolled back, so nothing is stored:

```bash
docker compose exec api python -m tools.eval.explanations --languages en,hi,or --pause 15
```

```bash
docker compose exec api python -m tools.eval.questions --pause 30
```

Rehearse the demonstration without internet ([`compose.offline.yaml`](compose.offline.yaml)): see what is ready offline, prepare explanations (and, with `--narrate --yes`, narration, which uses ElevenLabs characters), then run a report end to end on a throwaway account:

```bash
docker compose exec api python -m tools.offline check --email dev@nabz.local
```

```bash
docker compose -f compose.yaml -f compose.offline.yaml up -d
```

```bash
docker compose exec api python -m tools.offline rehearse
```

```bash
docker compose up -d
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

Everything lives in [`docs/`](docs/README.md): charter, requirements, architecture, data design, workflows, detailed design, project plan with Gantt chart, risk register, data sources and licensing, safety and privacy, test plan, security self-assessment, and architecture decision records; plus a [clinical review packet](docs/review/clinical-review-packet.md) and a [usability test plan](docs/review/usability-test-plan.md).

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
