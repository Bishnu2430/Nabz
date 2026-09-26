# ADR-0005 · Safety-critical logic is deterministic, not generated

**Status:** Accepted · 2026-09-26

## Context

Generative models can be fluent and wrong. In Nabz the worst failures are:

- missing a critical value
- mislabelling a result's status
- inventing a number
- stating a diagnosis or treatment

## Decision

- **Classification** (low / normal / high) and **critical-value detection** are plain, unit-tested code over clinician-reviewed tables. Critical alerts are fixed text, shown before any generated content.
- The LLM receives the *computed* statuses and insights as input, and only writes prose around them.
- A **validator** checks every generated explanation:
  - numbers match the input
  - status words match the computed status
  - required citations are present
  - no banned intents
  - an LLM judge agrees it is safe

  On any failure, a template built only from computed values is shown instead.
- Nothing is analysed until the **user confirms** the extracted values.

## Alternatives considered

| Option | Why not |
|---|---|
| Let the LLM classify and flag critical values | Non-deterministic; hard to test exhaustively; no clear accountability |
| Prompt-only safety ("do not diagnose") | Instructions reduce but do not remove unsafe output |
| No generation at all (templates only) | Safe but not understandable enough; fails objective O3 |

## Consequences

- Safety behaviour is testable with ordinary unit tests (TC-10, TC-13–TC-15) and a red-team suite in CI.
- Some good explanations will be rejected by strict number matching. That is acceptable; the fallback rate is monitored.
- The clinical advisor reviews tables and templates, not model weights.
