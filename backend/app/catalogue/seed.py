"""Load catalogue CSV data into the database. Safe to run repeatedly."""

from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.catalogue.data import CatalogueData
from app.catalogue.units import normalize_unit
from app.models import CriticalLimit, LabTest, OrganSystem, ReferenceRange, UnitConversion

RANGE_SOURCE = "Nabz catalogue default (adult, educational); the report's printed range takes precedence"
LIMIT_SOURCE = "Commonly published adult critical limits (draft, pending clinical review)"


@dataclass(frozen=True)
class SeedResult:
    organs: int
    tests: int
    conversions: int
    ranges: int
    limits: int


def seed_catalogue(session: Session, data: CatalogueData) -> SeedResult:
    for o in data.organs:
        stmt = insert(OrganSystem).values(
            code=o.code, name_en=o.name_en, name_hi=o.name_hi, name_or=o.name_or, mesh_ids=list(o.mesh_ids)
        )
        session.execute(stmt.on_conflict_do_update(
            index_elements=["code"],
            set_={"name_en": o.name_en, "name_hi": o.name_hi, "name_or": o.name_or, "mesh_ids": list(o.mesh_ids)},
        ))
    organ_ids = {code: id_ for code, id_ in session.execute(select(OrganSystem.code, OrganSystem.id))}

    for t in data.tests:
        values = {
            "loinc_code": t.loinc, "canonical_name": t.name, "short_name": t.short, "panel": t.panel,
            "aliases": list(t.aliases), "organ_system_id": organ_ids[t.organ], "canonical_unit": t.unit,
            "decimals": t.decimals, "plausible_min": t.plausible_min, "plausible_max": t.plausible_max,
            "cv_within_subject": t.cv_i, "cv_analytical": t.cv_a, "is_active": True,
        }
        stmt = insert(LabTest).values(code=t.code, **values)
        session.execute(stmt.on_conflict_do_update(index_elements=["code"], set_=values))
    test_ids = {code: id_ for code, id_ in session.execute(select(LabTest.code, LabTest.id))}

    # Child rows are replaced wholesale for the tests in the CSV.
    ids = [test_ids[t.code] for t in data.tests]
    for model in (UnitConversion, ReferenceRange, CriticalLimit):
        session.execute(delete(model).where(model.test_id.in_(ids)))
    session.add_all(
        UnitConversion(test_id=test_ids[c.test_code], from_unit=normalize_unit(c.from_unit), factor=c.factor,
                       offset=c.offset)
        for c in data.conversions
    )
    session.add_all(
        ReferenceRange(test_id=test_ids[r.test_code], sex=r.sex, age_min=r.age_min, age_max=r.age_max,
                       low=r.low, high=r.high, source=RANGE_SOURCE)
        for r in data.ranges
    )
    session.add_all(
        CriticalLimit(test_id=test_ids[m.test_code], low=m.low, high=m.high, message_key=m.message_key,
                      source=LIMIT_SOURCE)
        for m in data.limits
    )
    session.flush()
    return SeedResult(len(data.organs), len(data.tests), len(data.conversions), len(data.ranges),
                      len(data.limits))
