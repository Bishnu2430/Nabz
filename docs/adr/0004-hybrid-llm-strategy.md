# ADR-0004 · Hybrid LLM strategy

**Status:** Accepted · 2026-09-26

## Context

The stakeholder asked whether a 3B-parameter local model can do the work, or whether an API is needed. The development and demo machine is an Intel i5-1235U with 16 GB RAM and integrated graphics: **no CUDA GPU**, so local models run on the CPU. Nabz has several language and vision tasks:

1. Structuring ambiguous OCR rows into JSON and resolving unknown test aliases. The input is short, the output schema is fixed, and a human checks the result.
2. Reading a table directly from a difficult photo (vision).
3. Writing patient-facing explanations in English, Hindi and Odia. This must be faithful to the numbers, medically careful and fluent. It is safety-relevant.
4. Judging generated text for unsafe content.
5. Embedding passages for retrieval.

## Decision

| Task | Model | Size | Where |
|---|---|---|---|
| 1 · Row structuring (fallback after rules + fuzzy match) | Qwen3-4B-Instruct via Ollama | 3–4B (about 2.5 GB at 4-bit) | Local, CPU, optional profile |
| 2 · Vision fallback | `claude-opus-5` | Frontier API | API, **only with per-report consent** |
| 3 · Explanations EN/HI/OR | `claude-opus-5` | Frontier API | API, de-identified payload |
| 4 · Safety judge | `claude-opus-5` at low effort, plus deterministic rules | — | API + local rules |
| 5 · Embeddings | multilingual-e5-small | 118M | Local, CPU |

OCR is PaddleOCR, a specialised model and not an LLM. All generative calls go through an `LLMProvider` interface, and the choice is configuration (`LLM_PROVIDER`, `LLM_MODEL`, `LOCAL_LLM_MODEL`).

## Why a 3B model is not enough for explanations

- Hindi quality drops sharply below about 30B open models, and Odia is weak even in larger open models. The objective is ≥ 4/5 native-speaker rating (O5).
- Smaller models follow long safety instructions and citation requirements less reliably, and hallucinate numbers more often. The validator would reject more outputs and users would see the template fallback more often.
- A 7–8B vision-language model needs about 6–8 GB of GPU memory. On this CPU it would take minutes per page.

## Alternatives considered

| Option | Why not |
|---|---|
| Everything local with a 3B model | Fails the language-quality and safety objectives |
| Everything local with a 30B+ model | Needs a GPU with about 20–24 GB of memory; not available |
| Everything through the API (including row structuring) | Works, but sends more data out and costs more; the local path keeps structuring private and free |
| Fine-tune a small model on explanations | No labelled data, no GPU and no time; also weakens the "grounded, cited" guarantee |

## Consequences

- **Cost.** About US$0.06 per report per language for explanations (≈5k input + 1.5k output tokens at $5 / $25 per million tokens), before prompt caching. The project budget is US$30.
- **Privacy.** Only de-identified values leave the host by default ([10](../10-safety-privacy-compliance.md)).
- **Availability.** Explanations need internet. Offline demo mode covers the venue risk (R-06).
- **Flexibility.** If a GPU becomes available, a larger local model can be swapped in behind the same interface and compared with the same evaluation suite.
