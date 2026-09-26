# ADR-0001 · Record architecture decisions

**Status:** Accepted · 2026-09-26

## Context

Nabz is built by one developer, reviewed by a guide and presented by a team. Decisions made early (database, LLM strategy, safety design) will be questioned at the jury and are easy to forget or re-argue.

## Decision

Record every decision that affects structure, technology, data or safety as a short Markdown ADR in `docs/adr/`, numbered sequentially, using the sections Context, Decision, Alternatives considered and Consequences.

## Alternatives considered

- **Decisions in chat or commit messages.** Easy to lose, hard to cite in the report.
- **One big design document only.** It hides *why* choices were made and the options that were rejected.

## Consequences

- Five minutes of writing per decision.
- The report's design chapter and the jury Q&A can cite ADRs directly.
- New ADRs supersede old ones instead of editing history.
