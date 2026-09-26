# 01 · Project charter

| | |
|---|---|
| **Document ID** | NBZ-DOC-01 |
| **Version** | 0.1 · draft |
| **Owner** | Lead developer |
| **Reviewers** | Project guide, team members |
| **Last updated** | 2026-09-26 |

## 1. Summary

Nabz is a web application that reads a photo or PDF of a lab report and asks the user to confirm the extracted values. It then explains the results in plain English, Hindi or Odia, shows them on an interactive 3D model of the body, and tracks how each value changes across years of reports. It helps people understand their reports and prepare for their doctor. **It does not diagnose.**

## 2. Problem statement

Blood tests are among the most common health interactions in India. The result is usually a dense table of abbreviations, numbers and reference ranges that most people cannot read. Three gaps follow:

1. **Comprehension.** Patients, and the family members who look after them, do not know which values matter or what they mean. Web searches return generic and often alarming content.
2. **Continuity.** Nobody watches the *trend*. A value can stay "in range" while rising steadily for three years. Reports from different labs also use different units and ranges, so comparing them by hand is error-prone.
3. **Consultation time.** Doctor visits are short. Patients arrive without the right questions and forget what they were told.

## 3. Vision and objectives

**Vision.** Anyone holding a lab report can understand it in their own language within two minutes, and can walk into the next consultation with better questions.

| # | Objective (SMART) | Measure | Target by M3 (28 Sep 2026) |
|---|---|---|---|
| O1 | Extract report values accurately | Field-level accuracy before human review, on the evaluation set | ≥ 95 % clean scans · ≥ 90 % phone photos |
| O2 | Explain safely | Unsafe statements (diagnosis, dosing) in the red-team set | 0 |
| O3 | Explain understandably | Median time for a lay user to answer 3 questions about a report, Nabz vs raw report | ≥ 50 % faster (10-person test) |
| O4 | Show change over time | Reports whose trend and change-significance are computed correctly on synthetic histories | 100 % |
| O5 | Speak the user's language | Doctor-plus-native-speaker rating of Hindi and Odia explanations | ≥ 4 / 5 average |
| O6 | Demo reliably | End-to-end demo works with the network disconnected (cached mode) | Pass 3 of 3 rehearsals |

## 4. Scope

### In scope (MVP)

- Upload of JPG, PNG, HEIC or PDF reports; image-quality check; OCR and extraction of about 60 common tests (CBC, liver, kidney, lipid, thyroid, glucose/HbA1c, vitamins, iron, urine routine).
- A review screen where the user confirms or corrects every extracted value against the report image.
- Classification against the report's own reference ranges (falling back to catalogue ranges), fixed critical-value alerts, reference-change-value significance, trends, and population percentiles.
- Grounded explanations in English, Hindi and Odia with cited sources, a "questions for your doctor" list and optional voice narration.
- A 3D body map with organ systems coloured by status, a timeline scrubber and report↔organ linking.
- Accounts, family profiles, consent management, data export and deletion.
- Everything runs with Docker Compose on one machine, plus an offline demo mode.

### Out of scope

- Diagnosis, treatment, prescribing or dosing advice, and emergency triage.
- Imaging reports (X-ray, MRI), prescriptions and handwritten notes.
- Native mobile apps (the web app is mobile-first instead).
- Integration with lab systems or ABDM. This is listed as future scope in §11.
- Production cloud hosting, payments and multi-tenant scale.

## 5. Stakeholders

| Stakeholder | Interest | Involvement |
|---|---|---|
| Patients | Understand their own results | Primary users; usability testing |
| Caregivers (adult children, spouses) | Look after a family member's health remotely | Primary users; persona "Priya" |
| Doctors | Better-prepared patients; no misinformation | Clinical reviewer for explanations; secondary user (shared summary) |
| Project guide | Academic quality, timely delivery | Reviews each gate |
| Jury / evaluators | Relevance, novelty, execution | Final demo |
| Team members | Pitch, research, content | See RACI in [07](07-project-plan.md#6-raci) |

## 6. Deliverables

| Deliverable | Form | Due |
|---|---|---|
| Engineering documentation (this set) | Markdown + SVG in `docs/` | M0 · 7 Aug |
| Extraction MVP (upload → review) | Running containers + tests | M1 · 30 Aug |
| Feature-complete application | Web app, API, worker, database | M2 · 20 Sep |
| Evaluation report (accuracy, safety, usability) | Markdown + charts | M3 · 28 Sep |
| College project report (BPUT format) | DOCX / PDF | M3 · 28 Sep |
| Demo kit: offline mode, sample reports, poster, pitch deck | Files + rehearsed script | M3 · 28 Sep |

## 7. Success criteria

The project succeeds if, at M3, the objectives O1–O6 are met *and* a first-time user completes the demo flow (photo → body map → explanation in their language) without help in under three minutes.

## 8. Constraints

- **People.** One developer builds everything. Team members cover research, content, validation and the pitch.
- **Hardware.** Development and demo run on a laptop with an Intel i5-1235U, 16 GB RAM and integrated graphics (no CUDA GPU). This decides the LLM strategy: see [03 §7](03-system-architecture.md#7-llm-strategy-and-model-sizing).
- **Budget.** Student budget. External API spend is capped at about US$30 for the whole project, and no paid hosting is used.
- **Time.** About 9 weeks from 1 Aug to 30 Sep 2026, including public holidays.
- **Stack decisions.** PostgreSQL only (no SQLite), and everything containerised with Docker. See [ADR-0002](adr/0002-postgresql-single-datastore.md) and [ADR-0003](adr/0003-docker-compose-for-all-environments.md).

## 9. Assumptions

- Most reports that users hold are printed in English, even when the user prefers Hindi or Odia.
- A synthetic report generator plus a small set of consented, redacted real reports is enough to evaluate extraction.
- A clinician (for example from the college health centre) will review about 20 explanations.
- Internet is available at the venue, and offline mode covers the case where it is not.

## 10. High-level risks

Top risks are extraction accuracy on phone photos, unsafe or wrong explanations, Odia language quality, and single-developer bandwidth. The full list, with scoring and mitigations, is in the [risk register](08-risk-register.md).

## 11. Future scope

- **ABDM integration.** Pull reports directly from Health Information Providers through an ABHA-linked personal health record (FHIR R4 `DiagnosticReport` / `Observation`), removing the need for OCR.
- **More report types.** Prescriptions (medication timelines), imaging report summaries, and more Indian languages.
- **Clinician mode.** A structured summary view for doctors, and an "ask about this value" chat grounded in the same knowledge base.
- **Native apps.** Wrap the web app, and add offline OCR on the device.
- **Population insights.** Opt-in, anonymised trend data to support Indian-specific reference-interval research.

## 12. Approval

| Role | Name | Decision | Date |
|---|---|---|---|
| Project guide | | | |
| Lead developer | | | |

## Revision history

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-09-26 | First draft |
