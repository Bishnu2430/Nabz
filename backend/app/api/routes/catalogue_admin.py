"""The catalogue and the knowledge base on the console (FR-35, FR-36): administrators edit tests, aliases, units and
ranges, propose critical limits and manage knowledge documents; clinical reviewers decide on critical limits.
The work is done in app.services.catalogue_admin.
"""

from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_session, require_roles
from app.api.routes.ask import get_embedder
from app.knowledge.embed import Embedder
from app.models import AppUser, CriticalLimit, KbChunk, KbDocument, LabTest, OrganSystem, ReferenceRange, UnitConversion
from app.models.enums import UserRole
from app.schemas import (
    CatalogueRow,
    CatalogueTestOut,
    CatalogueTestPatch,
    ConversionIO,
    KbDocumentIn,
    KbDocumentOut,
    KnowledgeOut,
    LimitForReview,
    LimitProposalIn,
    LimitVerdictIn,
    RangeIO,
    RecheckOut,
    ReembedOut,
)
from app.services import audit
from app.services import catalogue_admin as cat

router = APIRouter(tags=["catalogue"])
admin = require_roles(UserRole.ADMIN)
reviewer = require_roles(UserRole.REVIEWER)


def _problem(e: cat.CatalogueProblem) -> HTTPException:
    return HTTPException(e.status, {"detail": e.detail, "code": e.code, **e.extra})


def _test(session: Session, code: str) -> LabTest:
    test = session.scalar(select(LabTest).where(LabTest.code == code))
    if test is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Test not found.")
    return test


def _embedder(embedder: Embedder | None) -> Embedder:
    if embedder is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            {"detail": "The embedding model isn't installed.", "code": "embedder_unavailable"})
    return embedder


# --- Tests ------------------------------------------------------------------------------------------------------------

@router.get("/v1/admin/catalogue", response_model=list[CatalogueRow])
def list_tests(q: str = "", session: Session = Depends(get_session), user: AppUser = Depends(admin)):  # noqa: B008
    counts = {}
    for model in (UnitConversion, ReferenceRange):
        counts[model] = dict(session.execute(select(model.test_id, func.count()).group_by(model.test_id)).all())
    limits = {m.test_id: m for m in session.scalars(select(CriticalLimit))}
    query = select(LabTest, OrganSystem.code).join(OrganSystem, OrganSystem.id == LabTest.organ_system_id)
    if q.strip():
        like = f"%{q.strip()}%"
        query = query.where(LabTest.canonical_name.ilike(like) | LabTest.short_name.ilike(like)
                            | LabTest.code.ilike(like) | func.array_to_string(LabTest.aliases, " ").ilike(like))
    rows = session.execute(query.order_by(OrganSystem.id, LabTest.canonical_name)).all()
    return [CatalogueRow(code=t.code, name=t.canonical_name, short_name=t.short_name, organ=organ,
                         unit=t.canonical_unit, aliases=len(t.aliases or []),
                         conversions=counts[UnitConversion].get(t.id, 0), ranges=counts[ReferenceRange].get(t.id, 0),
                         critical=cat.limit_out(session, limits.get(t.id)))
            for t, organ in rows]


@router.get("/v1/admin/catalogue/{code}", response_model=CatalogueTestOut)
def get_test(code: str, session: Session = Depends(get_session), user: AppUser = Depends(admin)):  # noqa: B008
    return cat.test_detail(session, _test(session, code))


def _apply(session: Session, test: LabTest, change) -> CatalogueTestOut:  # noqa: ANN001
    try:
        change()
    except cat.CatalogueProblem as e:
        session.rollback()
        raise _problem(e) from None
    session.commit()
    return cat.test_detail(session, test)


@router.patch("/v1/admin/catalogue/{code}", response_model=CatalogueTestOut)
def edit_test(code: str, body: CatalogueTestPatch, session: Session = Depends(get_session),  # noqa: B008
              user: AppUser = Depends(admin)):  # noqa: B008
    test = _test(session, code)
    return _apply(session, test, lambda: cat.update_test(session, user, test, body))


@router.put("/v1/admin/catalogue/{code}/conversions", response_model=CatalogueTestOut)
def put_conversions(code: str, body: list[ConversionIO], session: Session = Depends(get_session),  # noqa: B008
                    user: AppUser = Depends(admin)):  # noqa: B008
    test = _test(session, code)
    return _apply(session, test, lambda: cat.set_conversions(session, user, test, body))


@router.put("/v1/admin/catalogue/{code}/ranges", response_model=CatalogueTestOut)
def put_ranges(code: str, body: list[RangeIO], session: Session = Depends(get_session),  # noqa: B008
               user: AppUser = Depends(admin)):  # noqa: B008
    test = _test(session, code)
    return _apply(session, test, lambda: cat.set_ranges(session, user, test, body))


@router.put("/v1/admin/catalogue/{code}/critical-limit", response_model=CatalogueTestOut)
def propose_limit(code: str, body: LimitProposalIn, session: Session = Depends(get_session),  # noqa: B008
                  user: AppUser = Depends(admin)):  # noqa: B008
    """A proposal: the current limits keep applying until a clinical reviewer approves it."""
    test = _test(session, code)
    return _apply(session, test, lambda: cat.propose_limit(session, user, test, body))


# --- Critical limits: clinical review --------------------------------------------------------------------------------

@router.get("/v1/review/critical-limits", response_model=list[LimitForReview])
def limits_for_review(session: Session = Depends(get_session), user: AppUser = Depends(reviewer)):  # noqa: B008
    """Proposals first, then limits nobody has signed off yet, then the rest."""
    rows = session.execute(select(CriticalLimit, LabTest).join(LabTest, LabTest.id == CriticalLimit.test_id)).all()
    rows.sort(key=lambda r: (r[0].proposed_at is None, r[0].reviewed_at is not None, r[1].canonical_name))
    return [LimitForReview(code=t.code, name=t.canonical_name, unit=t.canonical_unit,
                           critical=cat.limit_out(session, m), ranges=cat.ranges_of(session, t)) for m, t in rows]


@router.post("/v1/review/critical-limits/{code}", response_model=RecheckOut)
def decide_limit(code: str, body: LimitVerdictIn, session: Session = Depends(get_session),  # noqa: B008
                 user: AppUser = Depends(reviewer)):  # noqa: B008
    test = _test(session, code)
    try:
        changed = cat.decide_limit(session, user, test, body.approve, body.note)
    except cat.CatalogueProblem as e:
        session.rollback()
        raise _problem(e) from None
    session.commit()
    limit = session.scalar(select(CriticalLimit).where(CriticalLimit.test_id == test.id))
    return RecheckOut(critical=cat.limit_out(session, limit), results_changed=changed)


# --- Knowledge documents -------------------------------------------------------------------------------------------

def _doc_out(session: Session, doc: KbDocument) -> KbDocumentOut:
    tests = session.scalars(select(LabTest.code).join(KbChunk, KbChunk.test_id == LabTest.id)
                            .where(KbChunk.document_id == doc.id).distinct()).all()
    chunks = session.scalar(select(func.count()).where(KbChunk.document_id == doc.id)) or 0
    return KbDocumentOut(id=doc.id, title=doc.title, source_org=doc.source_org, url=doc.url, license=doc.license,
                         language=doc.language, retrieved_at=doc.retrieved_at, chunks=chunks, tests=sorted(tests),
                         citations=cat.citations_of(session, doc.id))


@router.get("/v1/admin/knowledge", response_model=KnowledgeOut)
def knowledge(session: Session = Depends(get_session), user: AppUser = Depends(admin),  # noqa: B008
              embedder: Embedder | None = Depends(get_embedder)):  # noqa: B008
    docs = session.scalars(select(KbDocument).order_by(KbDocument.source_org, KbDocument.title)).all()
    return KnowledgeOut(documents=[_doc_out(session, d) for d in docs],
                        chunks=session.scalar(select(func.count()).select_from(KbChunk)) or 0,
                        embedder=getattr(embedder, "name", None))


@router.post("/v1/admin/knowledge", response_model=KbDocumentOut, status_code=status.HTTP_201_CREATED)
def add_document(body: KbDocumentIn, session: Session = Depends(get_session),  # noqa: B008
                 user: AppUser = Depends(admin), embedder: Embedder | None = Depends(get_embedder)):  # noqa: B008
    try:
        doc = cat.add_document(session, user, body, _embedder(embedder))
    except cat.CatalogueProblem as e:
        session.rollback()
        raise _problem(e) from None
    session.commit()
    return _doc_out(session, doc)


@router.post("/v1/admin/knowledge/reembed", response_model=ReembedOut)
def reembed_all(session: Session = Depends(get_session), user: AppUser = Depends(admin),  # noqa: B008
                embedder: Embedder | None = Depends(get_embedder)):  # noqa: B008
    started = time.monotonic()
    docs, chunks = cat.reembed(session, _embedder(embedder))
    audit.record(session, user.id, "knowledge.reembed", "kb_document", None, documents=docs, chunks=chunks)
    session.commit()
    return ReembedOut(documents=docs, chunks=chunks, ms=round((time.monotonic() - started) * 1000))


@router.post("/v1/admin/knowledge/{doc_id}/reembed", response_model=ReembedOut)
def reembed_one(doc_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                user: AppUser = Depends(admin), embedder: Embedder | None = Depends(get_embedder)):  # noqa: B008
    if session.get(KbDocument, doc_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    started = time.monotonic()
    docs, chunks = cat.reembed(session, _embedder(embedder), doc_id)
    audit.record(session, user.id, "knowledge.reembed", "kb_document", doc_id, chunks=chunks)
    session.commit()
    return ReembedOut(documents=docs, chunks=chunks, ms=round((time.monotonic() - started) * 1000))


@router.delete("/v1/admin/knowledge/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                    user: AppUser = Depends(admin)):  # noqa: B008
    """Explanations that cited it keep their text; they lose the link to its passages."""
    doc = session.get(KbDocument, doc_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    audit.record(session, user.id, "knowledge.delete", "kb_document", doc.id, title=doc.title,
                 citations=cat.citations_of(session, doc.id))
    session.delete(doc)
    session.commit()
