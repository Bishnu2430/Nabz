"""Write, check and store the explanation for one report and language (FR-21 – FR-25, ADR-0005).

The generated explanation is shown only if it passes every deterministic check and the LLM judge. Otherwise, and
whenever generation isn't allowed (a critical value, no external-AI consent, no model or knowledge base), the
template built from computed values is stored instead. Either way the person gets an explanation; `meta` records
which one and why, so the fallback rate can be monitored (problem codes only, no health data in logs).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.explain.llm import LLMError, LLMProvider
from app.explain.payload import build_payload
from app.explain.prompt import JUDGE_SCHEMA, PROMPT_VERSION, judge_messages, messages, output_schema
from app.explain.template import template_explanation
from app.explain.validator import Problem, validate
from app.knowledge.embed import Embedder
from app.knowledge.retrieve import retrieve
from app.models import Explanation, ExplanationCitation, KbChunk, KbDocument, Report
from app.models.enums import ConsentPurpose, SafetyStatus
from app.services.ingest import has_consent

log = logging.getLogger("nabz.explain")


@dataclass(frozen=True)
class Outcome:
    explanation: Explanation
    source: str  # "model" | "template"
    reason: str | None  # why the template was used
    problems: list[Problem]

    @property
    def rejected(self) -> dict | None:
        return (self.explanation.content.get("meta") or {}).get("rejected")


def explain_report(session: Session, report: Report, language: str, provider: LLMProvider | None,
                   embedder: Embedder | None, judge: bool = True) -> Outcome:
    payload = build_payload(session, report)
    reason: str | None = None
    if payload.critical:
        reason = "critical"  # no generated prose around a critical value
    elif not has_consent(session, report.profile_id, ConsentPurpose.EXTERNAL_AI):
        reason = "no_consent"
    elif provider is None:
        reason = "no_model"
    elif embedder is None:
        reason = "no_knowledge"

    problems: list[Problem] = []
    passages = []
    content: dict | None = None
    tokens_in = tokens_out = latency = 0
    model_id = "template"
    rejected: dict | None = None  # generated text that failed a check, kept for the clinical reviewer, never shown
    if reason is None:
        passages = retrieve(session, embedder, payload.focus)
        schema = output_schema([t.test_code for t in payload.focus], [p.label for p in passages])
        try:
            done = provider.complete_json(messages(payload, passages, language), schema, "explanation",
                                          effort=settings.llm_reasoning_effort)
            tokens_in, tokens_out, latency = done.input_tokens, done.output_tokens, done.latency_ms
            problems = validate(done.content, payload, passages, language)
            if not problems and judge:
                verdict = provider.complete_json(judge_messages(payload, done.content), JUDGE_SCHEMA, "safety_review",
                                                 effort="low", max_tokens=2000)
                tokens_in += verdict.input_tokens
                tokens_out += verdict.output_tokens
                latency += verdict.latency_ms
                if verdict.content.get("safe") is not True:
                    problems.append(Problem("judge", "; ".join(map(str, verdict.content.get("problems") or []))[:500]))
            if problems:
                reason = "validation"
                rejected = {"model": done.model, "content": done.content,
                            "problems": [{"code": p.code, "detail": p.detail} for p in problems]}
            else:
                content, model_id = done.content, done.model
        except LLMError as exc:
            reason = "provider_error"
            problems = [Problem("provider", str(exc))]

    if content is None:
        content = template_explanation(payload, language)
        passages = []
    source = "template" if model_id == "template" else "model"
    cited = {c for t in content.get("per_test", []) for c in t.get("citations", [])}
    used = [p for p in passages if p.label in cited]
    content = {
        **content,
        "sources": _sources(session, used),
        "meta": {"source": source, "reason": reason, "problems": [p.code for p in problems],
                 "focus": len(payload.focus), "results": payload.results_total, "rejected": rejected},
    }
    if problems:
        log.info("explanation for report %s (%s) used the template: %s", report.id, language,
                 ",".join(sorted({p.code for p in problems})))

    session.execute(delete(Explanation).where(Explanation.report_id == report.id, Explanation.language == language))
    explanation = Explanation(
        report_id=report.id, language=language, model_id=model_id, prompt_version=PROMPT_VERSION, content=content,
        safety_status=SafetyStatus.PASSED if source == "model" else SafetyStatus.FALLBACK,
        input_tokens=tokens_in or None, output_tokens=tokens_out or None, latency_ms=latency or None,
    )
    session.add(explanation)
    session.flush()
    for rank, p in enumerate(used, start=1):
        session.add(ExplanationCitation(explanation_id=explanation.id, kb_chunk_id=p.chunk_id, rank=rank))
    session.flush()
    return Outcome(explanation, source, reason, problems)


def _sources(session: Session, passages: list) -> list[dict]:
    """What the reader sees under "Sources": one entry per passage label, with its document."""
    if not passages:
        return []
    docs = {str(chunk_id): doc for chunk_id, doc in session.execute(
        select(KbChunk.id, KbDocument).join(KbDocument, KbDocument.id == KbChunk.document_id)
        .where(KbChunk.id.in_([p.chunk_id for p in passages]))
    )}
    out = []
    for p in passages:
        if (doc := docs.get(p.chunk_id)) is not None:
            out.append({"label": p.label, "title": doc.title, "url": doc.url, "organisation": doc.source_org,
                        "license": doc.license})
    return out
