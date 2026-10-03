# ADR-0013 · Questions about a report: rules decide first, the model writes last

**Status:** Accepted · 2026-10-01

## Context

A person reading their results wants to ask follow-up questions: "what does creatinine measure?", "which results are outside the range?". An open question box is also the easiest way to get a model to do what Nabz must never do (FR-24, [ADR-0005](0005-deterministic-safety-rules.md)):

- diagnose ("do I have kidney disease?");
- predict ("will I need dialysis?");
- prescribe ("what should I take to lower it?");
- reassure ("should I be worried?");
- or follow injected instructions ("ignore your rules …").

Some questions also call for a different answer altogether: someone with chest pain needs to be told to get help now, not given an explanation.

## Decision

Answering a question (FR-47) happens in three steps, in this order.

1. **Rules decide whether the question may be answered at all** (`app/explain/ask.py`). Regular expressions in English, Hindi and Odia sort the question into one of these, checked in this order:
   - an attempt to redirect the assistant;
   - an emergency;
   - a request for treatment;
   - a request for a diagnosis, prediction or reassurance.

   Each gets a fixed reply. For diagnosis and treatment, the reply also shows what the report itself says about the tests the question named. Questions about a test the report doesn't have, or about nothing in the report, also get a fixed reply. No model sees any of these questions.
2. **The rest is answered from the person's own data.**
   - **By rules:** the report's own sentences for the tests named (value, range, status, change, trend). In English, these are followed by the one or two MedlinePlus sentences that only describe the test: no numbers, no conditions, no interpretation.
   - **By the model:** only when every condition holds:
     - the person has given external-AI consent;
     - a model and the knowledge base are available;
     - no result is beyond a critical limit.
3. **A model's answer goes through the explanation's checks before anyone sees it:**
   - the same wording, number, script and citation checks;
   - and the judge, told that this is an answer to a question.

   If anything fails, the rule-built answer is shown instead. The blocked text is kept for the clinical reviewer (FR-48), never shown to the person. If the model itself declines a question, the person gets the fixed "Nabz can't answer that from this report" reply.

Every question and reply is stored, so the person can read them again. The questions are included in the export and erased with the report. The audit log records that a question was asked and how it was handled, never its text.

A red-team file of questions in three languages (`data/redteam/questions.jsonl`) holds:
- questions the rules must refuse;
- questions they must let through.

It drives the tests, and the safety console runs it on demand.

## Alternatives considered

| Option | Why not |
|---|---|
| Let the model decide what it may answer (system prompt only) | Prompt instructions reduce unsafe answers but don't remove them; a refusal would depend on wording the model chose |
| A classifier model in front of the answering model | Another model to evaluate, slower, and still probabilistic for the cases that matter most |
| Suggested questions only, no free text | Safe, but the most natural question ("is this bad?") would have nowhere to go, and the refusal itself teaches what Nabz is for |
| Rules only, never a model | Safe and fast, and the fallback whenever a condition isn't met; the model adds fuller, plainer wording when consent allows |

## Consequences

- Refusals are deterministic, tested and the same every time, in all three languages; the Hindi and Odia patterns are drafts pending native-speaker review (T2.5).
- The rules over-refuse a little. For example, "does exercise affect creatinine?" counts as lifestyle advice. That is the intended direction of error.
- Questions phrased in ways the patterns don't know can reach the model. The output checks and the judge remain the last line, as for explanations.
- The reviewer's queue shows every refusal and every blocked model answer, so wrong calls can be found and the patterns improved.
