# 11 · Test and evaluation plan

| | |
|---|---|
| **Document ID** | NBZ-DOC-11 |
| **Version** | 0.1 · draft |
| **Last updated** | 2026-09-26 |

## 1. Objectives

1. Show that every *Must* requirement in the [SRS](02-software-requirements-specification.md) works (verification).
2. Measure the AI components against the targets in the charter (evaluation).
3. Show that real people understand their reports faster and that clinicians find the explanations safe (validation).

## 2. Test levels

| Level | Scope | Tools | Runs |
|---|---|---|---|
| Static | Lint, types, formatting | ruff, mypy, ESLint, tsc | Every commit (CI) |
| Unit | Pure logic: unit conversion, range classification, critical rules, RCV, Theil–Sen, validator rules, parsers | pytest, Hypothesis (property tests for conversions) | Every commit |
| Integration | API + Postgres + worker with real SQL (SKIP LOCKED, pgvector) | pytest + testcontainers (PostgreSQL + pgvector image) | Every pull request |
| Contract | Explanation JSON schema; OpenAPI schema diff | jsonschema, schemathesis | Every pull request |
| End-to-end | Upload → review → confirm → insights in a browser | Playwright against `docker compose` | Nightly + before gates |
| AI evaluation | Extraction accuracy, confidence calibration, explanation safety and faithfulness | `backend/tests/eval` harness, frozen datasets | On demand + before gates |
| Performance | NFR-01–NFR-04 | Timed eval runs, Lighthouse, browser performance panel | Before M2, M3 |
| Security | ASVS L1 checklist, dependency audit, authorisation tests | pip-audit, npm audit, custom pytest | Before M2 |
| Usability | 10-person task test | Script + stopwatch + SUS questionnaire | Transition |

## 3. Test environments

| Environment | What | Data |
|---|---|---|
| Local | `docker compose up` on the developer laptop | Synthetic |
| CI | GitHub Actions runner with service containers | Synthetic, fixtures |
| Demo | Developer laptop in demo mode (`APP_ENV=demo`), offline cache enabled | Bundled sample reports only |

## 4. AI and data evaluation

| Metric | Definition | Dataset | Target |
|---|---|---|---|
| Field accuracy (clean) | Share of (test, value, unit, range) fields exactly correct after normalisation, **before** review | 500 synthetic PDFs | ≥ 95 % |
| Field accuracy (photo) | Same, on photographs | 180 photos | ≥ 90 % |
| Mapping accuracy | Share of rows mapped to the correct LOINC code | Both | ≥ 97 % |
| Unrecognised rate | Rows correctly flagged "not recognised" instead of mis-mapped | Rows with off-catalogue tests | ≥ 90 % |
| Confidence calibration | Expected calibration error of the row-confidence model | Held-out 20 % | ≤ 0.05 |
| Review efficiency | Share of wrong rows that fall below τ (and so are shown first) | Photo set | ≥ 90 % recall at ≤ 25 % of rows flagged |
| Trend correctness | Planted slope recovered within tolerance; RCV decision correct | 50 synthetic histories | 100 % |
| Critical-value recall | Critical values that raise the fixed alert | Rule table × boundary cases | 100 % |
| Safety | Red-team cases producing an unsafe final output | ≥ 60 red-team cases | 0 |
| Faithfulness | Explanations whose numbers and statuses all match the input | 100 generated explanations | 100 % after the validator |
| Readability | Flesch-Kincaid grade of English summaries | 100 explanations | ≤ 8 |
| Language quality | Native-speaker rating (1–5) for Hindi and Odia | 20 per language | ≥ 4.0 |
| Clinical acceptability | Clinician rating "safe and correct" | 20 explanations | 20 / 20 |
| Latency | p95 extraction; p95 explanation | Timed runs | ≤ 30 s; ≤ 20 s |

**Rules for fair evaluation.**

- Evaluation sets are frozen (hashed) at M1. The confidence model is trained only on the 80 % training split.
- Real samples are reported separately and never used for tuning.
- Every evaluation run records the git commit, model IDs and prompt version.

## 5. Traceability (Must requirements → tests)

| Requirement | Test cases |
|---|---|
| FR-01 | TC-01 |
| FR-02, FR-05 | TC-02 |
| FR-03, FR-04 | TC-03, TC-04 |
| FR-06–FR-08 | TC-05, AI eval (field accuracy) |
| FR-09–FR-11 | AI eval (mapping, calibration), TC-07 |
| FR-12 | TC-05 |
| FR-13–FR-15 | TC-06 |
| FR-16 | TC-08 |
| FR-17 | TC-10 |
| FR-18, FR-19 | TC-09, TC-11, AI eval (trend) |
| FR-21, FR-23, FR-24, FR-25 | TC-12–TC-16 |
| FR-22 | TC-17 |
| FR-27, FR-28 | TC-18 |
| FR-32, FR-33 | TC-19, TC-20 |
| FR-38 | TC-21 |

## 6. Test cases

Written in the college report format. *Status* is filled in when each case is executed.

| Test ID | Test case title | Test condition | System behaviour | Expected result | Status |
|---|---|---|---|---|---|
| TC-01 | Register and sign in | New email + valid password; then wrong password 5 times | Creates account; locks out after repeated failures | Session cookie set; 429 after the limit | Planned |
| TC-02 | Minor profile needs guardian confirmation | Create profile with DOB < 18 years ago | Blocks consent until guardian box is ticked | Consent saved only after confirmation | Planned |
| TC-03 | Upload without processing consent | Profile with processing consent off; upload PDF | Rejects upload | 403 problem response; no job created | Planned |
| TC-04 | No external call without AI consent | External-AI consent off; confirm report | Uses template explanation only | No outbound LLM request (mock asserts zero calls) | Planned |
| TC-05 | Clean PDF end to end | Synthetic one-page CBC PDF | Queued → processing → needs_review via SSE | All rows extracted; p95 time within NFR-01 | Planned |
| TC-06 | Review gate | Report in `needs_review`; call insights endpoint | Refuses to analyse | 409 until `/confirm` is called; then analysis runs | Planned |
| TC-07 | Unknown test flagged | Report containing a test not in the catalogue | Row mapped to nothing | Row shown as "not recognised", not mis-mapped | Planned |
| TC-08 | Range source fallback | Report row without a printed range; profile female, 45 | Uses catalogue range for sex and age | `ref_source = catalogue`, label shown in UI | Planned |
| TC-09 | Significant change | Two HbA1c values differing by more than the RCV | Marks change as significant | Badge "significant change"; not shown when below the RCV | Planned |
| TC-10 | Critical value | Potassium above the critical limit | Fixed alert first, before any generated text | Alert text equals the reviewed template exactly | Planned |
| TC-11 | Trend projection | Synthetic history with a planted upward slope | Theil–Sen slope and crossing date | Slope within ±10 % of planted; date shown | Planned |
| TC-12 | De-identified payload | Profile with name, DOB, phone | Builds LLM request | Payload contains no name, phone, exact DOB or image | Planned |
| TC-13 | Banned intent blocked | Mock LLM returns "You have diabetes, take metformin" | Validator fails | Template explanation shown; `safety_status = fallback` | Planned |
| TC-14 | Number mismatch blocked | Mock LLM text says 7.9 when value is 6.9 | Validator fails | Fallback used; event logged | Planned |
| TC-15 | Citations required | Mock LLM omits citations for one test | Validator fails | Fallback used | Planned |
| TC-16 | Doctor questions present | Normal flow | Explanation JSON has 3–6 questions | Rendered in UI and print view | Planned |
| TC-17 | Language switch | Switch EN → HI → OR on the insights page | Loads or generates each language | UI strings and explanation in the chosen script; no reload | Planned |
| TC-18 | Body map status | Report with high ALT, normal creatinine | Colours organ systems | Liver amber, kidneys green; click flies to liver card | Planned |
| TC-19 | Export | Request JSON and PDF export | Generates files | JSON validates against the export schema; PDF opens | Planned |
| TC-20 | Hard delete | Delete a profile with reports | Removes rows and files | No rows or files remain; one audit entry exists | Planned |
| TC-21 | Offline demo | Disconnect network; run demo script | Serves cached explanations and audio | Demo completes without errors | Planned |

## 7. Entry and exit criteria

| Gate | Entry | Exit |
|---|---|---|
| M1 | Extraction stage merged; eval harness runs | Field accuracy measured and reported; TC-05–TC-07 pass |
| M2 | All *Must* FRs merged | TC-01–TC-20 pass; red-team suite 0 failures; ASVS L1 checklist done |
| M3 | Feature freeze | All targets in §4 met or deviations documented with reasons; TC-21 passes 3 times |

## 8. Defect management

Defects are GitHub issues labelled `bug` with severity:

- **S1.** Safety or privacy failure. Fix before any demo.
- **S2.** Blocks the main flow.
- **S3.** Degraded feature.
- **S4.** Cosmetic.

Any S1 blocks the gate.

## Revision history

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-09-26 | First draft: 21 test cases |
