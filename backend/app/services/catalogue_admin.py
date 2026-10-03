"""Changing the catalogue and the knowledge base (FR-35, FR-36, docs/10 §4).

Every change is audited with what it was before and after, and raises the catalogue revision so the API and the
worker rebuild their copy. A new critical limit is only proposed by an administrator; it applies once a clinical
reviewer approves it, and approving re-checks every confirmed result of that test.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.catalogue.db import bump_revision
from app.catalogue.matcher import squash
from app.catalogue.units import normalize_unit
from app.knowledge.embed import Embedder
from app.models import (
    AppUser,
    AuditLog,
    CriticalLimit,
    Explanation,
    ExplanationCitation,
    KbChunk,
    KbDocument,
    LabTest,
    Observation,
    OrganSystem,
    Profile,
    ReferenceRange,
    Report,
    UnitConversion,
)
from app.models.enums import JobStage, Lang, ReportStatus
from app.schemas import (
    CatalogueChange,
    CatalogueTestOut,
    CatalogueTestPatch,
    ConversionIO,
    CriticalLimitOut,
    KbDocumentIn,
    LimitProposalIn,
    LimitProposalOut,
    RangeIO,
)
from app.services import audit
from app.services.analysis import analyse_profile
from app.worker import queue

CONFIRMED = (ReportStatus.VERIFIED, ReportStatus.ANALYSING, ReportStatus.EXPLAINING, ReportStatus.EXPLAINED)
ADMIN_RANGE_SOURCE = "Set by an administrator"
DEFAULT_MESSAGE = "critical.contact_doctor_today"


class CatalogueProblem(Exception):
    """A change that can't be made, with a code the console translates."""

    def __init__(self, status: int, code: str, detail: str, **extra: Any):
        super().__init__(detail)
        self.status, self.code, self.detail, self.extra = status, code, detail, extra


def _s(v: Decimal | None) -> str | None:
    return None if v is None else str(v)


def _change(session: Session, user: AppUser, action: str, test: LabTest, **meta: Any) -> None:
    audit.record(session, user.id, action, "lab_test", None, test=test.code, **meta)
    bump_revision(session)


# --- Reading ---------------------------------------------------------------------------------------------------------

def limit_out(session: Session, limit: CriticalLimit | None) -> CriticalLimitOut | None:
    if limit is None:
        return None
    proposed = None
    if limit.proposed_at is not None:
        proposed = LimitProposalOut(low=limit.proposed_low, high=limit.proposed_high, at=limit.proposed_at,
                                    by=limit.proposed_by,
                                    note=limit.proposal_note)
    return CriticalLimitOut(low=limit.low, high=limit.high, source=limit.source, reviewed_by=limit.reviewed_by,
                            reviewed_at=limit.reviewed_at, proposed=proposed)


def ranges_of(session: Session, test: LabTest) -> list[RangeIO]:
    return [RangeIO(sex=r.sex, age_min=r.age_min, age_max=r.age_max, low=r.low, high=r.high)
            for r in session.scalars(select(ReferenceRange).where(ReferenceRange.test_id == test.id)
                                     .order_by(ReferenceRange.id))]


def history(session: Session, code: str, limit: int = 30) -> list[CatalogueChange]:
    rows = session.execute(
        select(AuditLog, AppUser.email).outerjoin(AppUser, AppUser.id == AuditLog.actor_user_id)
        .where(AuditLog.action.like("catalogue.%"), AuditLog.meta["test"].astext == code)
        .order_by(AuditLog.id.desc()).limit(limit)).all()
    return [CatalogueChange(at=a.at, actor=email, action=a.action,
                            meta={k: v for k, v in (a.meta or {}).items() if k != "test"} or None) for a, email in rows]


def test_detail(session: Session, test: LabTest) -> CatalogueTestOut:
    organ = session.get(OrganSystem, test.organ_system_id)
    conversions = session.scalars(select(UnitConversion).where(UnitConversion.test_id == test.id)
                                  .order_by(UnitConversion.id))
    return CatalogueTestOut(
        code=test.code, loinc=test.loinc_code, name=test.canonical_name, short_name=test.short_name, panel=test.panel,
        organ=organ.code if organ else "", unit=test.canonical_unit, decimals=test.decimals,
        plausible_min=test.plausible_min, plausible_max=test.plausible_max, aliases=list(test.aliases or []),
        conversions=[ConversionIO(from_unit=c.from_unit, factor=c.factor, offset=c.offset) for c in conversions],
        ranges=ranges_of(session, test),
        critical=limit_out(session, session.scalar(select(CriticalLimit).where(CriticalLimit.test_id == test.id))),
        history=history(session, test.code),
    )


# --- Tests, aliases, units and ranges ---------------------------------------------------------------------------------

def _names_elsewhere(session: Session, test: LabTest) -> dict[str, str]:
    """Every name and alias of the other tests, squashed as the matcher compares them."""
    taken: dict[str, str] = {}
    for other in session.scalars(select(LabTest).where(LabTest.id != test.id)):
        for name in (other.canonical_name, other.short_name, *(other.aliases or [])):
            taken.setdefault(squash(name), other.code)
    return taken


def update_test(session: Session, user: AppUser, test: LabTest, patch: CatalogueTestPatch) -> None:
    fields = patch.model_dump(exclude_unset=True)
    if "aliases" in fields:
        seen, aliases = set(), []
        for raw in fields["aliases"] or []:
            alias = " ".join(raw.split())[:80]
            key = squash(alias)
            if key and key not in seen:
                seen.add(key)
                aliases.append(alias)
        taken = _names_elsewhere(session, test)
        for alias in aliases:
            if squash(alias) in taken:
                raise CatalogueProblem(409, "alias_taken", f"“{alias}” already names {taken[squash(alias)]}.",
                                       alias=alias, test=taken[squash(alias)])
        fields["aliases"] = aliases
    low = fields.get("plausible_min", test.plausible_min)
    high = fields.get("plausible_max", test.plausible_max)
    if low is None or high is None or low >= high:
        raise CatalogueProblem(422, "plausible_order", "The lowest believable value must be below the highest.")
    columns = {"name": "canonical_name", "short_name": "short_name", "aliases": "aliases", "decimals": "decimals",
               "plausible_min": "plausible_min", "plausible_max": "plausible_max"}
    before, after = {}, {}
    for field, value in fields.items():
        column = columns[field]
        old = getattr(test, column)
        if field in ("name", "short_name"):
            value = value.strip()
        if old != value:
            before[field], after[field] = (_s(old), _s(value)) if isinstance(old, Decimal) else (old, value)
            setattr(test, column, value)
    if after:
        _change(session, user, "catalogue.test", test, before=before, after=after)


def set_conversions(session: Session, user: AppUser, test: LabTest, rows: list[ConversionIO]) -> None:
    canonical = normalize_unit(test.canonical_unit)
    units = [normalize_unit(r.from_unit) for r in rows]
    if canonical in units:
        raise CatalogueProblem(422, "conversion_canonical", f"{test.canonical_unit} is already this test's own unit.")
    if len(set(units)) != len(units):
        raise CatalogueProblem(422, "conversion_duplicate", "Each unit can be listed once.")
    current = select(UnitConversion).where(UnitConversion.test_id == test.id).order_by(UnitConversion.id)
    before = [[c.from_unit, str(c.factor), str(c.offset)] for c in session.scalars(current)]
    session.execute(delete(UnitConversion).where(UnitConversion.test_id == test.id))
    session.add_all(UnitConversion(test_id=test.id, from_unit=u, factor=r.factor, offset=r.offset)
                    for u, r in zip(units, rows, strict=True))
    after = [[u, str(r.factor), str(r.offset)] for u, r in zip(units, rows, strict=True)]
    if before != after:
        _change(session, user, "catalogue.conversions", test, before=before, after=after)


def set_ranges(session: Session, user: AppUser, test: LabTest, rows: list[RangeIO]) -> None:
    """The ranges used only when a report prints none. Reports already read keep the range they were read with."""
    for r in rows:
        if (r.low is None and r.high is None) or (r.low is not None and r.high is not None and r.low >= r.high) \
                or r.age_min > r.age_max:
            raise CatalogueProblem(422, "range_invalid", "Each range needs a low or a high value, low below high, "
                                                         "and the youngest age no older than the oldest.")
    before = [r.model_dump(mode="json") for r in ranges_of(session, test)]
    session.execute(delete(ReferenceRange).where(ReferenceRange.test_id == test.id))
    session.add_all(ReferenceRange(test_id=test.id, sex=r.sex, age_min=r.age_min, age_max=r.age_max, low=r.low,
                                   high=r.high, source=ADMIN_RANGE_SOURCE) for r in rows)
    after = [r.model_dump(mode="json") for r in rows]
    if before != after:
        _change(session, user, "catalogue.ranges", test, before=before, after=after)


# --- Critical limits: proposed by an administrator, decided by a clinical reviewer ------------------------------------

def propose_limit(session: Session, user: AppUser, test: LabTest, body: LimitProposalIn) -> CriticalLimit:
    if body.low is not None and body.high is not None and body.low >= body.high:
        raise CatalogueProblem(422, "limit_order", "The low critical limit must be below the high one.")
    limit = session.scalar(select(CriticalLimit).where(CriticalLimit.test_id == test.id))
    if limit is None:
        if body.low is None and body.high is None:
            raise CatalogueProblem(422, "limit_empty", "This test has no critical limit to remove.")
        limit = CriticalLimit(test_id=test.id, low=None, high=None, message_key=DEFAULT_MESSAGE,
                              source="Proposed by an administrator")
        session.add(limit)
    limit.proposed_low, limit.proposed_high = body.low, body.high
    limit.proposed_by, limit.proposed_at, limit.proposal_note = user.email, datetime.now(UTC), body.note.strip()
    session.flush()
    audit.record(session, user.id, "catalogue.limit_proposed", "lab_test", None, test=test.code,
                 current=[_s(limit.low), _s(limit.high)], proposed=[_s(body.low), _s(body.high)],
                 note=body.note.strip())
    return limit


def decide_limit(session: Session, user: AppUser, test: LabTest, approve: bool, note: str | None) -> int:
    """Approve or reject the proposal; approving with no proposal signs off the current limits. Returns how many
    confirmed results changed status."""
    limit = session.scalar(select(CriticalLimit).where(CriticalLimit.test_id == test.id))
    if limit is None:
        raise CatalogueProblem(404, "limit_missing", "This test has no critical limit.")
    pending = limit.proposed_at is not None
    if not approve and not pending:
        raise CatalogueProblem(409, "no_proposal", "There is no proposed change to reject.")
    before = [_s(limit.low), _s(limit.high)]
    if approve:
        if pending:
            limit.low, limit.high = limit.proposed_low, limit.proposed_high
            limit.source = "Proposed by an administrator, approved in clinical review"
        limit.reviewed_by, limit.reviewed_at = user.email, date.today()
    limit.proposed_low = limit.proposed_high = limit.proposed_by = limit.proposed_at = limit.proposal_note = None
    session.flush()
    action = "catalogue.limit_approved" if approve else "catalogue.limit_rejected"
    _change(session, user, action, test, before=before, after=[_s(limit.low), _s(limit.high)], note=note)
    return recheck_test(session, test.id) if approve and pending else 0


def recheck_test(session: Session, test_id: int) -> int:
    """Re-analyse every confirmed result of one test; reports whose statuses change are explained again."""
    rows = session.execute(
        select(Observation, Report).join(Report, Report.id == Observation.report_id)
        .where(Observation.test_id == test_id, Report.deleted_at.is_(None), Report.status.in_(CONFIRMED))).all()
    before = {o.id: o.status for o, _ in rows}
    for profile_id in {r.profile_id for _, r in rows}:
        analyse_profile(session, profile_id, {test_id})
    session.flush()
    changed = [(o, r) for o, r in rows if o.status != before[o.id]]
    for report in {r.id: r for _, r in changed}.values():
        languages = set(session.scalars(select(Explanation.language).where(Explanation.report_id == report.id)))
        session.execute(delete(Explanation).where(Explanation.report_id == report.id))
        fallback = session.scalar(select(Profile.preferred_language).where(Profile.id == report.profile_id))
        for language in languages or {fallback or Lang.EN}:
            queue.enqueue(session, report.id, JobStage.EXPLAIN, args={"lang": language.value})
    return len(changed)


# --- Knowledge documents --------------------------------------------------------------------------------------------

def chunk_text(title: str, text: str, max_words: int = 120) -> list[tuple[str, str]]:
    """(section, text) pairs: paragraphs joined up to about `max_words`; a line starting with # starts a section."""
    out: list[tuple[str, str]] = []
    section, buf = title, []

    def flush() -> None:
        if buf:
            out.append((section, " ".join(buf)))
            buf.clear()

    for para in re.split(r"\n\s*\n", text.strip()):
        para = " ".join(para.split())
        if not para:
            continue
        if para.startswith("#"):
            flush()
            section = para.lstrip("#").strip() or title
            continue
        if buf and len(" ".join(buf).split()) + len(para.split()) > max_words:
            flush()
        buf.append(para)
    flush()
    return out


def add_document(session: Session, user: AppUser, body: KbDocumentIn, embedder: Embedder) -> KbDocument:
    test = session.scalar(select(LabTest).where(LabTest.code == body.test_code))
    if test is None:
        raise CatalogueProblem(422, "unknown_test", "That test isn't in the catalogue.")
    if session.scalar(select(KbDocument.id).where(KbDocument.url == body.url)):
        raise CatalogueProblem(409, "kb_duplicate", "A document with that address is already in the knowledge base.")
    pieces = chunk_text(body.title.strip(), body.text)
    doc = KbDocument(title=body.title.strip(), source_org=body.source_org.strip(), url=body.url,
                     license=body.license.strip(), language=body.language,
                     retrieved_at=body.retrieved_at or date.today(),
                     checksum=hashlib.sha256(body.text.encode()).hexdigest())
    session.add(doc)
    session.flush()
    vectors = embedder.embed([f"{doc.title}. {section}\n{text}" for section, text in pieces], "passage")
    session.add_all(KbChunk(document_id=doc.id, test_id=test.id, chunk_index=i, content=f"{section}\n{text}",
                            language=doc.language, embedding=vector, token_count=len(text.split()))
                    for i, ((section, text), vector) in enumerate(zip(pieces, vectors, strict=True)))
    audit.record(session, user.id, "knowledge.add", "kb_document", doc.id, test=test.code, chunks=len(pieces))
    session.flush()
    return doc


def reembed(session: Session, embedder: Embedder, doc_id: uuid.UUID | None = None) -> tuple[int, int]:
    """Embed the chunks again in place (after a model change), so citations keep pointing at them."""
    query = select(KbChunk, KbDocument.title).join(KbDocument, KbDocument.id == KbChunk.document_id)
    if doc_id is not None:
        query = query.where(KbChunk.document_id == doc_id)
    rows = session.execute(query.order_by(KbChunk.document_id, KbChunk.chunk_index)).all()
    for start in range(0, len(rows), 64):
        batch = rows[start:start + 64]
        vectors = embedder.embed([f"{title}. {chunk.content}" for chunk, title in batch], "passage")
        for (chunk, _), vector in zip(batch, vectors, strict=True):
            chunk.embedding = vector
    session.flush()
    return len({c.document_id for c, _ in rows}), len(rows)


def citations_of(session: Session, doc_id: uuid.UUID) -> int:
    return session.scalar(select(func.count()).select_from(ExplanationCitation).join(
        KbChunk, KbChunk.id == ExplanationCitation.kb_chunk_id).where(KbChunk.document_id == doc_id)) or 0
