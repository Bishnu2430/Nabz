# ADR-0007 · Groq `openai/gpt-oss-120b` for explanations

**Status:** Accepted · 2026-09-26 · supersedes the API provider and model in [ADR-0004](0004-hybrid-llm-strategy.md)

## Context

ADR-0004 split the work between a small local model (row structuring) and an API model (patient-facing explanations, safety judge, vision fallback), and named a specific API model. The project has since chosen Groq as the API provider, with `openai/gpt-oss-120b` as the explanation model.

## Decision

| Setting | Value |
|---|---|
| `LLM_PROVIDER` | `groq` |
| `LLM_MODEL` | `openai/gpt-oss-120b`: explanations, doctor questions, safety judge |
| `VISION_MODEL` | A Groq-hosted vision model (default `meta-llama/llama-4-scout-17b-16e-instruct`). Used only for the consent-gated photo fallback, because gpt-oss-120b is text-only |
| `GROQ_API_KEY` | In `.env` only |

The local/API split, the `LLMProvider` interface, de-identified payloads and the safety validator from ADR-0004 and ADR-0005 are unchanged. A `GroqProvider` implements `LLMProvider` and uses JSON-schema structured output where the model supports it. It always validates the returned JSON itself.

## Consequences

- **Cost** drops by more than an order of magnitude compared with the earlier estimate: well under US$0.01 per report per language at Groq's list prices.
- **Latency** is low on Groq's hardware, which helps NFR-02 (p95 ≤ 20 s).
- **Language quality is the open question.** gpt-oss-120b's Hindi and especially Odia quality must be measured in Sprint 5 with the native-speaker rating (objective O5). If Odia falls short, the documented fallback applies: generate in English and translate with IndicTrans2 plus the project glossary (risk R-03).
- **Model lifecycle.** Groq retires and renames models. Model IDs are configuration, and the evaluation suite is re-run whenever they change.
- **Open weights.** gpt-oss-120b has open weights (Apache-2.0). If a GPU with enough memory ever becomes available, the same model could be self-hosted without changing prompts.
