# Architecture decision records

An ADR captures one significant decision: its context, the options considered, the choice and its consequences. ADRs are never edited after acceptance. A changed decision gets a new ADR that supersedes the old one.

| ADR | Title | Status | Date |
|---|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted | 2026-09-26 |
| [0002](0002-postgresql-single-datastore.md) | PostgreSQL as the single datastore (records, queue, vectors) | Accepted | 2026-09-26 |
| [0003](0003-docker-compose-for-all-environments.md) | Docker Compose for every environment | Accepted | 2026-09-26 |
| [0004](0004-hybrid-llm-strategy.md) | Hybrid LLM strategy: small local model + API for explanations | Accepted (provider superseded by 0007) | 2026-09-26 |
| [0005](0005-deterministic-safety-rules.md) | Safety-critical logic is deterministic, not generated | Accepted | 2026-09-26 |
| [0006](0006-3d-rendering-stack.md) | 3D body map with react-three-fiber and Z-Anatomy | Accepted | 2026-09-26 |
| [0007](0007-groq-gpt-oss-for-explanations.md) | Groq `openai/gpt-oss-120b` for explanations (supersedes the provider in 0004) | Accepted | 2026-09-26 |
| [0008](0008-elevenlabs-for-narration.md) | ElevenLabs for narration | Accepted | 2026-09-26 |
| [0009](0009-text-layer-first-and-rapidocr.md) | Text layer first, then RapidOCR | Accepted | 2026-09-27 |
| [0010](0010-analysis-methods.md) | How Nabz judges change and trends | Accepted | 2026-09-28 |
| [0011](0011-grounded-explanations.md) | Grounded, checked explanations | Accepted | 2026-09-30 |

Template: copy `0001` and follow the sections Context → Decision → Alternatives → Consequences.
