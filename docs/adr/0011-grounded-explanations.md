# ADR-0011 · Grounded, checked explanations

**Status:** Accepted · 2026-09-30 · implements FR-21 – FR-26 within [ADR-0004](0004-hybrid-llm-strategy.md), [ADR-0005](0005-deterministic-safety-rules.md), [ADR-0007](0007-groq-gpt-oss-for-explanations.md) and [ADR-0008](0008-elevenlabs-for-narration.md)

## Context

Sprint 5 turns analysed results into a plain-language explanation in English, Hindi or Odia, narrated on request. The earlier ADRs fixed the providers and the rule that safety-critical logic is deterministic. What remained open was:

- where grounding passages come from;
- how retrieval works within a free-tier rate limit;
- exactly which checks an explanation must pass;
- when the model isn't asked at all.

Live runs in this sprint answered most of these. The first drafts named diseases for single out-of-range values, and copied US reference thresholds from passages. One draft even contained a stray Chinese character.

## Decision

1. **Knowledge from MedlinePlus Connect.**
   - The source is NLM's web service, queried by each catalogue test's LOINC code. No pages are scraped.
   - For lab tests it returns the whole NLM lab-test page. The sections about what the test is, what it is used for and what results mean are kept; procedure, preparation, risks and references are dropped.
   - Pages with licensed A.D.A.M. content are rejected. The rest is public domain.
   - Result: 46 documents and 436 passages covering all 70 catalogue tests (urea and urine pus cells borrow the BUN and urinalysis pages). They're committed as `data/knowledge/chunks.jsonl`, with `manifest.csv`, so the base can be rebuilt offline.
2. **Retrieval.**
   - Embeddings come from `intfloat/multilingual-e5-small` as an int8 ONNX export on ONNX Runtime (already in the image for OCR), so no PyTorch is needed.
   - Vectors live in pgvector. Retrieval is filtered by test and ranked by cosine distance.
   - **One passage per test, trimmed to about 130 words**, so a whole report fits the free tier's 8,000 tokens a minute.
3. **Generation.**
   - `gpt-oss-120b` writes to a strict JSON schema whose enums pin the test codes and citation labels to the input.
   - Reasoning effort is low, because reasoning tokens count against the rate limit.
   - The prompt (`explain-v3`) forbids naming diseases or conditions. Possible causes are described in everyday words, with "your doctor can tell which applies".
   - The lab's range is always used, never a threshold from a passage.
   - Significant changes and confirmed trends are always mentioned.
4. **Deterministic validator.** Every one of these must pass:
   - language and script, with no letters from any other script;
   - all focus tests covered in order, each with its computed status;
   - citations drawn from that test's own passages, and no passage labels in the prose;
   - every number present in the de-identified input;
   - length limits;
   - no banned intents (diagnosis, treatment or dosing, reassurance, instruction-like text) in English, Hindi or Odia, after Unicode normalisation.
5. **LLM judge**, a second call at low effort, reviews what passed the rules. General, hedged statements pass. Anything pointing at the reader's own condition fails.
6. **Template fallback.** An explanation built only from computed values is stored whenever:
   - a value is critical (no generated prose ever appears around a critical value);
   - the person hasn't consented to external AI;
   - the model or knowledge base is unavailable;
   - the model errors after retries;
   - any check fails.

   The rejected draft is kept in the explanation's metadata for the clinical reviewer and never shown to the reader.
7. **Narration** is generated on first play, with voice consent. `eleven_multilingual_v2` lacks Odia (confirmed from `GET /v1/models`), so Odia uses `eleven_v4`.

## Alternatives considered

- **Scraping MedlinePlus pages.** Connect returns the same NLM content through a supported service with attribution rules, so scraping adds nothing.
- **sentence-transformers on PyTorch.** It adds about 800 MB to the image for the same vectors.
- **Two or more passages per test.** It pushed one report to about 9,700 tokens and hit the 8,000 tokens-a-minute limit before the judge could run.
- **Letting the model name possible conditions**, as the passages do. The judge rejected most drafts, and naming one disease for one value reads as a diagnosis to a lay reader.
- **Generating around critical values.** The fixed banner already says what matters; generated text could only soften or confuse it.

## Consequences

- Every explanation shown is either checked model text or the template, and the reader sees which ([11 §12](../11-test-and-evaluation-plan.md#12-sprint-5-explanation-results)).
- On the free tier, the worker writes about one explanation a minute (it waits out `retry-after`). A paid tier removes this limit without code changes.
- The Hindi and Odia banned-phrase lists and template wording are drafts until the native-speaker review (T2.5). The judge and the script check cover gaps meanwhile.
