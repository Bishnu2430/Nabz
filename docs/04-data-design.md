# 04 · Data design

| | |
|---|---|
| **Document ID** | NBZ-DOC-04 |
| **Version** | 0.1 · draft |
| **Database** | PostgreSQL 17 with `vector`, `pg_trgm`, `pgcrypto`, `citext` |
| **Last updated** | 2026-09-26 |

## 1. Principles

- **PostgreSQL is the single source of truth** for records, the job queue, alias search and embeddings ([ADR-0002](adr/0002-postgresql-single-datastore.md)). Files live on the `uploads` volume and are referenced by `storage_key`.
- **Raw and interpreted values are both kept.** `observation.raw_*` stores what the report said, and the typed columns store what we understood. This allows audits and re-processing.
- **Catalogue is data.** Tests, aliases, units, ranges and critical limits are rows administrators can edit, not code constants.
- **UUID primary keys** for user-facing entities (not guessable), and integer keys for catalogue tables.
- **Soft delete only where the law needs a trail.** A deletion request removes content immediately. `deleted_at` exists only so the nightly purge can confirm file removal before dropping rows.
- **Schema changes go through Alembic migrations**, never manual DDL. `infra/db/init` only enables extensions.

## 2. Entity–relationship diagram

![Entity–relationship diagram](diagrams/er-diagram.svg)

Account, role and session tables planned for Sprint 6 are specified in [12 §3](12-ux-and-access-design.md#3-authentication).

## 3. Table catalogue

| Domain | Table | Purpose | Approx. rows (demo) |
|---|---|---|---|
| Identity & consent | `app_user` | Account holder; login identity | 10s |
| | `profile` | Person whose reports are managed (self, parent, child) | 10s |
| | `consent` | Per-profile, per-purpose consent with policy version | 100s |
| Reports & extraction | `report` | One uploaded lab report and its lifecycle status | 100s |
| | `report_file` | Original file metadata; the file itself is on the volume | 100s |
| | `report_page` | Page image dimensions and raw OCR output (JSONB) | 100s |
| | `processing_job` | Durable queue item per pipeline stage | 1,000s |
| | `observation` | One result row: raw text, typed value, range, status, confidence | 10,000s |
| Clinical catalogue | `organ_system` | Organ systems and their 3D mesh IDs | ~15 |
| | `lab_test` | Supported tests: LOINC code, aliases, canonical unit, biological variation | ~60 → 150 |
| | `unit_conversion` | Unit → canonical unit factors per test | ~200 |
| | `reference_range` | Default ranges by sex and age when the report has none | ~300 |
| | `critical_limit` | Clinician-reviewed critical thresholds | ~40 |
| | `population_percentile` | NHANES percentiles by sex and age band | ~2,000 |
| Knowledge, AI & analytics | `kb_document` | Knowledge source with licence and URL | ~150 |
| | `kb_chunk` | Retrieval passage with 384-d embedding | ~3,000 |
| | `explanation` | Generated explanation (JSON), model and prompt version, safety status | 100s |
| | `explanation_citation` | Which passages an explanation cited | 1,000s |
| | `trend_insight` | Computed change, trend and percentile per profile × test | 1,000s |
| Governance | `share_link` | Expiring read-only links for doctors | 10s |
| | `feedback` | Thumbs up/down and comments on explanations | 100s |
| | `audit_log` | Append-only access and change log | 10,000s |

## 4. Enumerations

| Type | Values |
|---|---|
| `report_status` | `uploaded`, `rejected`, `queued`, `processing`, `needs_review`, `verified`, `analysing`, `explaining`, `explained`, `failed`, `deleted` |
| `job_stage` | `extract`, `analyse`, `explain`, `narrate` |
| `job_status` | `queued`, `running`, `succeeded`, `failed` |
| `obs_status` | `low`, `normal`, `high`, `critical_low`, `critical_high`, `unknown` |
| `consent_purpose` | `processing`, `external_ai`, `voice`, `research` |
| `safety_status` | `passed`, `fallback`, `blocked` |
| `sex` | `female`, `male`, `other`, `unknown` (reference ranges fall back to sex-neutral when not `female`/`male`) |
| `lang` | `en`, `hi`, `or` |
| `user_role` | `user`, `admin` |

## 5. Data dictionary: core tables

### 5.1 `report`

| Column | Type | Null | Description |
|---|---|---|---|
| `id` | uuid | no | PK, `gen_random_uuid()` |
| `profile_id` | uuid | no | FK → `profile.id`, `ON DELETE CASCADE` |
| `uploaded_by` | uuid | no | FK → `app_user.id` |
| `lab_name` | text | yes | As printed; extracted |
| `collected_at` | date | yes | Sample collection date; extracted, user-confirmed |
| `status` | report_status | no | See [state machine](05-workflows-and-interactions.md#5-report-lifecycle) |
| `source_sha256` | text | no | Hash of the original file; detects duplicate uploads per profile |
| `created_at` | timestamptz | no | default `now()` |
| `deleted_at` | timestamptz | yes | Set on delete request; purge job removes the row |

Indexes: `(profile_id, collected_at DESC)`; unique `(profile_id, source_sha256)` where `deleted_at IS NULL`.

### 5.2 `observation`

| Column | Type | Null | Description |
|---|---|---|---|
| `id` | uuid | no | PK |
| `report_id` | uuid | no | FK → `report.id`, cascade |
| `report_page_id` | uuid | yes | FK → `report_page.id`; null for rows added by hand |
| `test_id` | int | yes | FK → `lab_test.id`; null = not recognised |
| `raw_name`, `raw_value`, `raw_unit`, `raw_range` | text | yes | Exactly as read |
| `raw_flag` | text | yes | Flag printed on the report (`H` / `L`); cross-checked against the computed status |
| `section` | text | yes | Panel code of the report section the row appeared in (`cbc`, `lipid`, …); context for the catalogue matcher |
| `value_num` | numeric | yes | Parsed value in canonical unit |
| `unit` | text | yes | Canonical unit |
| `ref_low`, `ref_high` | numeric | yes | Range in canonical unit |
| `ref_source` | text | no | `report` or `catalogue` |
| `status` | obs_status | no | From the classifier |
| `bbox` | jsonb | yes | `{x, y, w, h}` in page pixels for highlighting |
| `confidence` | real | no | Calibrated probability, 0–1 |
| `verified_at` | timestamptz | yes | Set when the user confirms the report |
| `edited` | boolean | no | True if the user changed any field |

Indexes: `(report_id)`; `(test_id)`; history query uses `report.profile_id` + `test_id` via a join on the indexed report columns.

### 5.3 `lab_test`

| Column | Type | Description |
|---|---|---|
| `id` | int | PK |
| `code` | text | Unique stable slug used by seeds and code (e.g. `hba1c`) |
| `loinc_code` | text | Unique LOINC code (e.g. `4548-4` for HbA1c); check digit validated on load |
| `short_name`, `panel` | text | Display label and report section (`cbc`, `lipid`, `liver`, …) |
| `canonical_name` | text | Display name in English; translations in the i18n bundle |
| `aliases` | text[] | Spellings seen on Indian reports ("HbA1c", "Glycated Haemoglobin", "GHb"…). Matched in memory with rapidfuzz, as the catalogue is small; `pg_trgm` stays available for admin search |
| `organ_system_id` | smallint | FK → `organ_system.id`; drives the 3D colouring |
| `canonical_unit` | text | UCUM unit |
| `plausible_min`, `plausible_max` | numeric | Physiological bounds for sanity checks (not reference ranges) |
| `cv_analytical`, `cv_within_subject` | real | Biological-variation inputs for RCV |

### 5.4 `processing_job`

| Column | Type | Description |
|---|---|---|
| `id` | bigint | PK, identity |
| `report_id` | uuid | FK → `report.id`, cascade |
| `stage` | job_stage | Which handler runs it |
| `status` | job_status | Queue state |
| `attempts` | smallint | Incremented on claim; three attempts maximum |
| `run_after` | timestamptz | Back-off: `now() + 2^attempts × 10 s` |
| `locked_at` | timestamptz | Stale-lock recovery after 10 min |
| `error` | text | Last error message (no health data) |

Partial index: `(run_after) WHERE status = 'queued'`.

### 5.5 `explanation`

| Column | Type | Description |
|---|---|---|
| `content` | jsonb | `{summary, per_test[], doctor_questions[], disclaimer}`; schema versioned by `prompt_version` |
| `model_id` | text | e.g. `openai/gpt-oss-120b` or `template` for the safe fallback |
| `safety_status` | safety_status | Validator result |
| `input_tokens`, `output_tokens`, `latency_ms` | int | Cost and performance accounting |
| `audio_key` | text | Storage key of the narration, if any |

### 5.6 `kb_chunk`

| Column | Type | Description |
|---|---|---|
| `embedding` | vector(384) | multilingual-e5-small, normalised; HNSW index with `vector_cosine_ops` |
| `test_id` | int | Optional filter so retrieval stays on-topic |
| `language` | lang | Passages can be English originals or reviewed translations |

## 6. Retention and deletion

| Data | Retention | Mechanism |
|---|---|---|
| Report files, pages, observations, explanations | Until the user deletes them or the account | Immediate delete of content; purge job clears rows within 30 days |
| Consent records | Account lifetime + 1 year (evidence of consent) | Kept after withdrawal, marked `revoked_at` |
| `audit_log` | 1 year | Monthly partition drop |
| Evaluation datasets (synthetic) | Project lifetime | In the repository (`data/synthetic`) |
| Consented real samples | Until M3 + 30 days | Encrypted folder outside git (`data/private`); deleted after evaluation |

## 7. Migrations and seed data

- Alembic revision per change, named `YYYYMMDD_short_description`.
- Seed data comes from CSV files in [`data/catalogue/`](../data/catalogue/README.md) (10 organ systems, 70 tests, unit conversions, default ranges, critical limits). It is validated on load (LOINC check digits, units, bounds) and loaded by an idempotent command: `python -m app.cli seed-catalogue`. The catalogue CSV is reviewed like code.
- The knowledge base is loaded by an ingestion command that records licence and checksum in `kb_document`, chunks the text (about 300 tokens with 15 % overlap), embeds it and writes to `kb_chunk`.

## Revision history

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-09-26 | First draft: 22 tables |
