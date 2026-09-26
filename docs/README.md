# Nabz documentation

> *For centuries, doctors read your nabz (pulse) to understand your body. Nabz reads your lab report and shows you your body.*

Nabz turns a photo or PDF of a blood-test report into a verified, plain-language explanation in English, Hindi or Odia. It maps each result onto a 3D model of the body and tracks results across years. This folder is the engineering source of truth for the project. Every document is versioned with the code, and every figure is generated from source in [`diagrams/src`](diagrams/src).

| | |
|---|---|
| **Baseline** | v0.1 · M0 documentation baseline (draft) |
| **Status** | Draft for review by the project guide |
| **Owner** | Lead developer |

## Document map

| # | Document | Answers | Key figures |
|---|---|---|---|
| 01 | [Project charter](01-project-charter.md) | Why are we building this, what is in scope, and how do we define success? | — |
| 02 | [Software requirements specification](02-software-requirements-specification.md) | What must the system do, and how well? | Use-case model |
| 03 | [System architecture](03-system-architecture.md) | How is it built, which technology does what, and how big an LLM do we need? | Architecture, deployment |
| 04 | [Data design](04-data-design.md) | What do we store, and how is it related? | ER diagram |
| 05 | [Workflows & interactions](05-workflows-and-interactions.md) | How does a report flow through the system and the user's day? | Pipeline, activity, sequence, state machine, user journey |
| 06 | [Detailed design](06-detailed-design.md) | What modules, classes and APIs exist? | Class diagram |
| 07 | [Project plan](07-project-plan.md) | How and when will it be delivered, and by whom? | Life cycle, Gantt |
| 08 | [Risk register](08-risk-register.md) | What could go wrong, and what are we doing about it? | Heat map |
| 09 | [Data sources & licensing](09-data-sources-and-licensing.md) | Which datasets and knowledge sources do we need, and may we use them? | — |
| 10 | [Safety, privacy & compliance](10-safety-privacy-compliance.md) | How do we stay safe, private and on the right side of regulation? | Threat model |
| 11 | [Test & evaluation plan](11-test-and-evaluation-plan.md) | How do we prove it works? | Test cases |
| — | [Architecture decision records](adr/README.md) | Why did we choose X over Y? | — |

**Suggested reading order.** A new reader should start with 01 → 02 → 03. The guide or jury version is 01 plus the figures in 03 and 05. Before writing code, read 04, 06 and the ADRs.

## Figures

All diagrams live in [`diagrams/`](diagrams) as standalone SVG files, so they render on GitHub, in VS Code and in Word, and scale cleanly for the printed report. They use one visual language: the Nord palette, grouped boundaries with a corner tag, icon tiles and numbered steps.

| Figure | File | Used in |
|---|---|---|
| System architecture | [architecture.svg](diagrams/architecture.svg) | 03 |
| Deployment topology | [deployment.svg](diagrams/deployment.svg) | 03 |
| Report processing pipeline | [pipeline.svg](diagrams/pipeline.svg) | 05 |
| Use-case model | [use-case.svg](diagrams/use-case.svg) | 02 |
| Activity diagram | [activity.svg](diagrams/activity.svg) | 05 |
| Sequence diagram | [sequence.svg](diagrams/sequence.svg) | 05 |
| Report state machine | [state-machine.svg](diagrams/state-machine.svg) | 05 |
| User journey map | [user-journey.svg](diagrams/user-journey.svg) | 05 |
| Entity–relationship diagram | [er-diagram.svg](diagrams/er-diagram.svg) | 04 |
| Class diagram | [class-diagram.svg](diagrams/class-diagram.svg) | 06 |
| Project life cycle | [lifecycle.svg](diagrams/lifecycle.svg) | 07 |
| Gantt chart | [gantt.svg](diagrams/gantt.svg) | 07 |

To regenerate the figures after changing their source data, run this from the repository root. It needs Python 3.10 or newer and no packages:

```bash
python docs/diagrams/src/build.py
```

**Report editions.** [`diagrams/report/`](diagrams/report) holds A4-sized versions of every figure for the college report. They are drawn at print size (602 px portrait / 930 px landscape, smallest text ≈ 7 pt) and written in centimetres, so inserting them into Word at 100 % gives the right size. Large figures are split into parts (a) and (b). Rebuild them with `python docs/diagrams/src/report.py`.

The Gantt chart reads its dates from [`diagrams/src/schedule.csv`](diagrams/src/schedule.csv). Move a date there and rebuild; don't edit the SVG.

## Mapping to the college project report

The university report (BPUT format, 40–60 pages) is assembled from these documents in the Transition phase. The table shows where each chapter's material comes from.

| Report chapter | Source |
|---|---|
| 1 Introduction: purpose, scope, problem definition | 01 §2–§4, 02 §1 |
| 2 Literature survey: system review, technology used | 03 §6 (technology), 09; related-work survey is a team task in Sprint 7 |
| 3 Requirement analysis: language, OS, hardware | 02 §2.4 and §4–§5, 03 §5 |
| 4 Project planning: system model | 07 §1–§4 (life cycle, Gantt) |
| 5 System design: use case, activity, class and block diagrams | 02 §3, 05 §3, 06 §2, 03 §3 (block diagram = architecture), 04 §2 |
| 6 System testing: test cases and results | 11 §6 (table already in the college format) |
| 7 Implementation: workflow, source code | 05 §2, 06 §3–§5 |
| 8 Screenshots | captured during Transition |
| 9 Conclusion and future scope | 01 §11 |
| 10 References (IEEE) | collect in 09 as sources are used |

## Conventions

- **IDs.** FR-xx functional requirement · NFR-xx non-functional · UC-xx use case · R-xx risk · TC-xx test case · ADR-xxxx decision · M0–M3 milestones.
- **Status words.** *Draft* (open for change) → *Baselined* (approved at a gate; change via the change log) → *Superseded*.
- **Change control.** Each document ends with a revision history. A change to a baselined requirement needs a line in that history and, if it affects the schedule, an updated `schedule.csv`.
- **Language.** Indian English spelling. Dates are ISO (2026-09-26) in tables and "26 Sep 2026" in prose.
