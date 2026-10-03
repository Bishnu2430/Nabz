"""The catalogue as stored in the database, where administrators edit it (FR-35). The CSV files in data/catalogue
seed it; after that the database is the source the API and the worker read."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalogue.data import (
    CatalogueData,
    ConversionRow,
    LimitRow,
    OrganRow,
    PercentileRow,
    RangeRow,
    TestRow,
)
from app.models import (
    CatalogueRevision,
    CriticalLimit,
    LabTest,
    OrganSystem,
    PopulationPercentile,
    ReferenceRange,
    UnitConversion,
)


def revision(session: Session) -> int:
    return session.scalar(select(CatalogueRevision.revision).where(CatalogueRevision.id == 1)) or 0


def bump_revision(session: Session) -> int:
    """Called with every change to the catalogue, in the same transaction."""
    row = session.get(CatalogueRevision, 1, with_for_update=True)
    if row is None:
        row = CatalogueRevision(id=1, revision=0)
        session.add(row)
    row.revision = (row.revision or 0) + 1
    row.changed_at = datetime.now(UTC)
    session.flush()
    return row.revision


def catalogue_from_db(session: Session) -> CatalogueData | None:
    """Everything the interpreter needs, read from the tables; None when the catalogue hasn't been seeded."""
    organs = {o.id: o for o in session.scalars(select(OrganSystem))}
    tests = session.scalars(select(LabTest).order_by(LabTest.id)).all()
    if not tests:
        return None
    code = {t.id: t.code for t in tests}
    data = CatalogueData()
    data.organs = [OrganRow(o.code, o.name_en, o.name_hi, o.name_or, tuple(o.mesh_ids or ())) for o in organs.values()]
    data.tests = [TestRow(code=t.code, loinc=t.loinc_code, name=t.canonical_name, short=t.short_name, panel=t.panel,
                          organ=organs[t.organ_system_id].code, unit=t.canonical_unit, decimals=t.decimals,
                          plausible_min=t.plausible_min, plausible_max=t.plausible_max, cv_i=t.cv_within_subject,
                          cv_a=t.cv_analytical, aliases=tuple(t.aliases or ())) for t in tests]
    data.conversions = [ConversionRow(code[c.test_id], c.from_unit, c.factor, c.offset)
                        for c in session.scalars(select(UnitConversion).order_by(UnitConversion.id))]
    data.ranges = [RangeRow(code[r.test_id], r.sex.value, r.age_min, r.age_max, r.low, r.high)
                   for r in session.scalars(select(ReferenceRange).order_by(ReferenceRange.id))]
    data.limits = [LimitRow(code[m.test_id], m.low, m.high, m.message_key)
                   for m in session.scalars(select(CriticalLimit).order_by(CriticalLimit.id))]
    data.percentiles = [PercentileRow(code[p.test_id], p.sex.value, p.age_band.lower, p.age_band.upper - 1,
                                      (p.p05, p.p25, p.p50, p.p75, p.p95), p.n)
                        for p in session.scalars(select(PopulationPercentile).order_by(PopulationPercentile.id))]
    return data
