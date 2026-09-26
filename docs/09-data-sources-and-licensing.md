# 09 · Data sources and licensing

| | |
|---|---|
| **Document ID** | NBZ-DOC-09 |
| **Version** | 0.1 · draft |
| **Last updated** | 2026-09-26 |

## 1. Do we need to train a model?

**Mostly no.** Nabz does not fine-tune an LLM. The AI parts need three kinds of data, none of them a "diagnosis book":

| Need | Used for | Source type |
|---|---|---|
| **Reference data** | Deciding what a value is (catalogue, units, ranges, critical limits, biological variation, population percentiles) | Standards and public statistical datasets (§2) |
| **Knowledge for grounding** | What the LLM may say about each test. Retrieved and cited, never memorised | Curated, licence-checked consumer-health sources (§3) |
| **Evaluation data** | Proving that extraction and explanations work; training two small models (the row-confidence classifier and quality thresholds) | Synthetic reports with ground truth, photographed prints, a few consented real reports (§4) |

**Why no medical textbooks or diagnosis books.**

1. Nabz does not diagnose. Diagnostic material would push the model towards exactly the statements the validator must block.
2. Textbooks such as Harrison's or Robbins are copyrighted, and ingesting them into a RAG index is not permitted.
3. A small, curated, per-test knowledge base (about 150 documents) is easier to review, cite and keep correct than a book.

## 2. Reference and standards data

| Source | What we take | Licence / terms | Where it lands |
|---|---|---|---|
| **LOINC** (Regenstrief Institute) | Codes and names for about 60 → 150 common tests | Free; requires a LOINC account and acceptance of the LOINC licence; attribution | `lab_test.loinc_code` |
| **UCUM** (Unified Code for Units of Measure) | Canonical unit strings and conversions | Free to use with attribution | `lab_test.canonical_unit`, `unit_conversion` |
| **The lab's own printed range** | Primary reference range for every observation | Part of the user's document | `observation.ref_low/high` (`ref_source = report`) |
| **Open references for default ranges** | Fallback ranges when a report prints none, by age and sex | Cite each range's source; clinician review | `reference_range` |
| **Published critical-limit lists** | Critical thresholds (e.g. potassium, sodium, glucose, haemoglobin, platelets) | Cite the source; must be **reviewed by the project's clinical advisor** before use | `critical_limit` |
| **EFLM Biological Variation Database** | Within-subject (CVI) and analytical (CVA) variation per test, for the reference change value | Free online access; check the terms before redistributing values, cite in the UI | `lab_test.cv_within_subject`, `cv_analytical` |
| **NHANES laboratory data** (US CDC / NCHS) | Survey-weighted percentiles of common tests by age and sex | Public domain | `population_percentile` (labelled "US population, NHANES") |
| **ICMR guidelines** (e.g. type 2 diabetes management) | Indian thresholds and wording for context (e.g. HbA1c bands) | Government publication; cite, don't copy wholesale | Knowledge base + validator reference |

**Indian reference intervals.** Robust public datasets of Indian population reference intervals are limited. That is why Nabz always prefers the lab's printed range and labels any NHANES-based comparison as a US population (risk R-14).

## 3. Knowledge base for grounded explanations

| Source | Content | Licence / terms | Use |
|---|---|---|---|
| **MedlinePlus lab-test pages** (US NLM) | Plain-language "what is this test, what do results mean" pages | NLM-authored content is in the public domain. Some MedlinePlus pages contain licensed third-party content (e.g. A.D.A.M.) that **must not** be copied. Check per page | Primary English source, chunked + embedded |
| **MedlinePlus Connect** | Web service that returns MedlinePlus pages for a LOINC code | Free service; attribution | Linking from each test card; helps curation |
| **StatPearls** (NCBI Bookshelf) | Clinician-level background on lab tests | CC BY-NC-ND 4.0: non-commercial, no derivatives | Retrieval **only for the academic prototype**; replace before any commercial use |
| **ICMR / MoHFW public health material** | Indian context (diabetes, anaemia, thyroid) | Government publications; cite | Selected passages |
| **Project-written summaries** | Short per-test explainers in EN, reviewed by the clinical advisor, translated to HI/OR by native speakers | Owned by the team | Preferred passages for HI/OR retrieval |

Every document is recorded in `data/knowledge/manifest.csv` with URL, date retrieved, licence and checksum, and in the `kb_document` table. Anything without a clear licence is not ingested.

## 4. Evaluation and training data

| Dataset | How we get it | Size target | Ground truth | Used for |
|---|---|---|---|---|
| **Synthetic reports** | Generator renders realistic reports (3–5 layouts modelled on common Indian formats, **no real lab branding**) from sampled values with Faker for names | 500 PDFs | Exact, because we generated them | Extraction accuracy on clean input; confidence-model training |
| **Photographed synthetic reports** | Print about 60 synthetic reports; photograph them in varied light, angles and folds with 3 phones | 180 photos | Exact (same source) | Photo accuracy; quality-gate thresholds; confidence-model training |
| **Consented real reports** | Team families; written consent; names, IDs and QR codes redacted before storage | 15–25 | Hand-labelled by two people, disagreements resolved | Realism check; reported separately |
| **Synthetic histories** | 3–5 reports per synthetic person with planted trends (stable, drifting, sudden change) | 50 people | Planted parameters | Trend, RCV and projection correctness |
| **Red-team prompts** | Values and injected text designed to provoke diagnosis, dosing, reassurance about critical values, or prompt injection through OCR text | ≥ 60 cases | Expected verdict | Safety validator and explanation tests |
| **Clinical review set** | 20 explanations across EN/HI/OR | 20 | Clinician and native-speaker ratings | O2 / O5 objectives |

Real samples are stored only in `data/private/`, which is git-ignored and on an encrypted disk. They are deleted 30 days after M3.

## 5. Models and services

| Component | Model / service | Licence | Notes |
|---|---|---|---|
| OCR | PaddleOCR PP-OCRv5 | Apache-2.0 | CPU inference in the worker |
| Embeddings | intfloat/multilingual-e5-small | MIT | 384-d; supports Hindi; Odia retrieval quality to be verified in Sprint 5 |
| Local LLM | Qwen3-4B-Instruct (via Ollama) | Apache-2.0 | Optional; row structuring only |
| Explanation LLM | Groq API, `openai/gpt-oss-120b` (open-weight model, Apache-2.0) | Groq API terms | De-identified payloads only |
| Vision fallback | Groq API, vision model set in `VISION_MODEL` | Groq API terms; model licence | Only with per-report consent |
| Translation aid | AI4Bharat IndicTrans2 | MIT | Fallback when direct generation in Odia is weak (R-03) |
| Text-to-speech | Candidates: Sarvam AI (commercial API), AI4Bharat Indic Parler-TTS (open source) | Check each | Chosen in Sprint 5 after an Odia voice-quality test |
| 3D anatomy | Z-Anatomy (derived from BodyParts3D) | CC BY-SA 4.0 | Attribution on the About screen; modified meshes are shared under the same licence |
| Fonts | Noto Sans, Noto Sans Devanagari, Noto Sans Oriya | SIL OFL 1.1 | UI in all three scripts |

## 6. Attribution screen (to ship in the app)

The About page will list: LOINC ("This material contains content from LOINC®…" as required by its licence), NHANES (CDC/NCHS), MedlinePlus (NLM), EFLM biological-variation data, Z-Anatomy (CC BY-SA 4.0), Noto fonts (OFL), and every open-source library through an auto-generated licence list.

## 7. References (IEEE style, to extend as sources are used)

[1] Regenstrief Institute, "LOINC — Logical Observation Identifiers Names and Codes." [Online]. Available: https://loinc.org

[2] Centers for Disease Control and Prevention, National Center for Health Statistics, "National Health and Nutrition Examination Survey (NHANES)." [Online]. Available: https://www.cdc.gov/nchs/nhanes/

[3] U.S. National Library of Medicine, "MedlinePlus: Medical Tests." [Online]. Available: https://medlineplus.gov/lab-tests/

[4] European Federation of Clinical Chemistry and Laboratory Medicine, "EFLM Biological Variation Database." [Online]. Available: https://biologicalvariation.eu

[5] PaddlePaddle, "PaddleOCR." [Online]. Available: https://github.com/PaddlePaddle/PaddleOCR

[6] Z-Anatomy, "Z-Anatomy: an open-source 3D atlas of anatomy." [Online]. Available: https://www.z-anatomy.com

*Access dates are added when the source is ingested. Check each URL at that time.*

## Revision history

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-09-26 | First draft |
