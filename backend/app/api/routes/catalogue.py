from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.models import LabTest, OrganSystem
from app.schemas import CatalogueTest

router = APIRouter(prefix="/v1/catalogue", tags=["catalogue"])


@router.get("/tests", response_model=list[CatalogueTest])
def list_tests(session: Session = Depends(get_session)):  # noqa: B008
    """Tests the review screen can map a row to (public reference data)."""
    rows = session.execute(
        select(LabTest, OrganSystem.code).join(OrganSystem, OrganSystem.id == LabTest.organ_system_id)
        .where(LabTest.is_active).order_by(LabTest.panel, LabTest.canonical_name)
    ).all()
    return [CatalogueTest(code=t.code, name=t.canonical_name, short_name=t.short_name, panel=t.panel,
                          unit="" if t.canonical_unit == "ratio" else t.canonical_unit, organ=organ)
            for t, organ in rows]
