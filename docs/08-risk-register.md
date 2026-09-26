# 08 · Risk register

| | |
|---|---|
| **Document ID** | NBZ-DOC-08 |
| **Version** | 0.1 · draft |
| **Review cadence** | Every Sunday retrospective; re-baselined at each gate |
| **Last updated** | 2026-09-26 |

**Scoring.** Likelihood (L) and Impact (I) are each rated 1–5. Score = L × I: **15–25 high**, 8–14 medium, 1–7 low. Owners: Dev = developer, Team = team members.

## 1. Heat map

| Likelihood ↓ / Impact → | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| **5** | | | | | |
| **4** | | | R-05 | R-01 | |
| **3** | | R-10 | R-03, R-11, R-13 | R-04, R-06, R-09 | R-02 |
| **2** | | R-12 | R-14 | R-08 | R-07 |
| **1** | | | | | |

## 2. Register

| ID | Risk (cause → effect) | L | I | Score | Mitigation | Contingency / trigger | Owner |
|---|---|---|---|---|---|---|---|
| R-01 | Phone photos are skewed, shadowed or folded → extraction accuracy falls below target → wrong values reach review | 4 | 4 | **16** | Client-side quality gate with retake tips; OpenCV deskew/denoise; confidence model sends weak rows to review first; photo evaluation set from week 2 | If photo accuracy < 85 % at M1: enable the consent-gated vision fallback for low-quality pages | Dev |
| R-02 | LLM writes a diagnosis, dosing advice or a wrong number → user harm, loss of trust | 3 | 5 | **15** | Human confirmation before explanation; rules own critical values; structured output; validator (number match, banned intents, citations); safe template fallback; red-team suite in CI | Any red-team failure blocks the release; switch the affected language to template-only | Dev |
| R-03 | Odia output is unnatural or wrong → requirement FR-22 (Odia) unmet | 3 | 3 | 9 | Curated EN–HI–OR glossary; native-speaker review; generate in English, then translate with glossary constraints if direct generation is weak | If rating < 3.5 / 5 at M2: ship Odia as "beta" with audio off | Team |
| R-04 | 3D body model too heavy for integrated graphics → low frame rate on the demo laptop | 3 | 4 | 12 | Spike in Sprint 1; decimate meshes in Blender; Draco/meshopt compression; organ-level LOD; cap device pixel ratio | If < 45 fps: stylised low-poly body; 2D fallback always available | Dev |
| R-05 | One developer does all the building → illness, exams or burnout stall the project | 4 | 3 | 12 | Prioritised backlog (Must first); weekly scope check; documentation and ADRs keep knowledge out of one head; no heroics before exams | If > 1 week lost: drop *Could* items and one *Should* sprint | Dev |
| R-06 | Internet unavailable or slow at the venue → explanations and audio fail live | 3 | 4 | 12 | Offline demo mode with cached explanations and audio for sample reports; phone hotspot as backup | Switch to offline mode during the demo; practise once in rehearsal | Dev |
| R-07 | Real report data leaks (laptop lost, repository made public, logs) → privacy harm | 2 | 5 | 10 | Real samples only in encrypted, git-ignored `data/private/`; BitLocker; secrets in `.env`; no health data in logs; delete samples after M3 | Incident: revoke keys, notify affected people, record in the incident log | Dev + Team |
| R-08 | Jury or regulator sees Nabz as a diagnostic medical device | 2 | 4 | 8 | Wording "understand, not diagnose" everywhere; out-of-scope list in UI and docs; safety chapter in the report | Prepared answer and citation of the scope statement in Q&A | Team |
| R-09 | Too few real Indian report samples → evaluation not representative | 3 | 4 | 12 | Synthetic generator with several layouts; team collects about 20 consented, redacted samples from families; photograph printed synthetic reports under varied conditions | If < 10 real samples by 28 Aug: report results on synthetic + photographed sets and state the limitation | Team |
| R-10 | Docker on Windows uses too much memory or is slow → development friction | 3 | 2 | 6 | `.wslconfig` limit of 10 GB; local LLM behind a profile; bind mounts only for source code | Run Ollama natively on Windows if WSL memory is tight | Dev |
| R-11 | Scope creep (chat, more report types, native app) → core features late | 3 | 3 | 9 | Charter scope list; every new idea goes to "future scope" unless it replaces something | Guide arbitrates at the next gate | Dev |
| R-12 | Licence non-compliance (Z-Anatomy CC BY-SA, LOINC terms, NC-licensed text) → takedown or academic penalty | 2 | 2 | 4 | Licence manifest per source ([09](09-data-sources-and-licensing.md)); attribution screen; no NC content in commercial plans | Replace the offending source; regenerate embeddings | Team |
| R-13 | External API price or availability changes → budget exceeded or outage | 3 | 3 | 9 | Token accounting per report; prompt caching; `LLMProvider` interface allows switching; offline cache | Budget alert at US$20: reduce demo traffic, pre-generate | Dev |
| R-14 | Reference ranges and percentiles from non-Indian populations mislead users | 2 | 3 | 6 | Prefer the lab's own printed range; label catalogue and NHANES sources clearly; explain the limitation in the UI | Hide percentiles for tests where population differences are known to be large | Dev |

## 3. Closed risks

None yet.

## Revision history

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-09-26 | Initial register: 14 risks |
