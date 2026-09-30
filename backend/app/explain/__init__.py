"""Plain-language explanations (Sprint 5, FR-21 – FR-26).

Pipeline for one report and language:

1. `payload`: the confirmed results and their analysis, de-identified (FR-25).
2. `app.knowledge`: retrieve passages for the tests worth explaining.
3. `prompt` + `llm`: the model writes JSON that follows a strict schema.
4. `validator`: deterministic checks (numbers, statuses, citations, script, banned intents), then an LLM judge.
5. `template`: on any failure, or when a value is critical, or without external-AI consent, an explanation built
   only from computed values is used instead (ADR-0005).
"""
