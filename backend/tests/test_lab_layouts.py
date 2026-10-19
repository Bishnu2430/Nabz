"""A report laid out like a large Indian chain's: a methodology column between the name and the value, a summary
page that repeats the results outside their range, reference tables printed under the results, and urine results
in words. Every result must be read once, under the right test, and nothing else."""

import io
from pathlib import Path

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.catalogue import CatalogueData
from app.models import LabTest, Observation
from app.services.ingest import ingest_report
from app.storage import LocalVolumeStorage
from app.worker.runner import Worker
from app.worker.stages import ExtractionStage
from tests.factories import make_profile

pytestmark = pytest.mark.db


def _report() -> bytes:
    buf = io.BytesIO()
    c = Canvas(buf, pagesize=A4)
    height = A4[1]

    def row(y: float, *cells: tuple[float, str]) -> None:
        for x, text in cells:
            c.drawString(x, height - y, text)

    def header(method: str) -> None:
        c.setFont("Helvetica", 9)
        row(60, (45, "TEST NAME"), (241, method), (362, "VALUE"), (427, "UNITS"), (483, "Bio. Ref. Interval."))

    # page 1: the summary of results outside their range, repeated in full on page 2
    c.setFont("Helvetica", 9)
    row(40, (45, "Tests Outside Reference Range"))
    row(60, (45, "Test Name"), (240, "Observed Value"), (330, "Units"), (400, "Bio. Ref. Interval."))
    row(80, (45, "LDL CHOLESTEROL - DIRECT"), (240, "131"), (330, "mg/dL"), (400, "< 100"))
    c.showPage()
    # page 2: lipids with the method used, then the lab's reference table
    header("TECHNOLOGY")
    row(80, (45, "TOTAL CHOLESTEROL"), (242, "PHOTOMETRY"), (363, "204"), (425, "mg/dL"), (483, "< 200"))
    row(95, (45, "HDL CHOLESTEROL - DIRECT"), (242, "PHOTOMETRY"), (363, "34"), (425, "mg/dL"), (483, "40-60"))
    row(110, (45, "LDL CHOLESTEROL - DIRECT"), (242, "PHOTOMETRY"), (363, "131"), (425, "mg/dL"), (483, "< 100"))
    row(125, (45, "TRIG / HDL RATIO"), (242, "CALCULATED"), (363, "3.17"), (425, "Ratio"), (483, "< 3.12"))
    row(140, (45, "LDL / HDL RATIO"), (242, "CALCULATED"), (363, "3.9"), (425, "Ratio"), (483, "1.5-3.5"))
    row(170, (49, "DESIRABLE"), (150, "<200"), (299, "<100"), (340, "NORMAL"), (400, "<150"))
    row(185, (49, "BORDERLINE HIGH"), (150, "200-239"), (209, "HIGH"), (250, ">60"))
    c.showPage()
    # page 3: urine, mostly in words
    header("METHODOLOGY")
    row(80, (44, "COLOUR"), (242, "Visual Determination"), (363, "Yellow"), (425, "-"), (483, "Pale Yellow"))
    row(95, (44, "URINARY PROTEIN"), (242, "PEI"), (363, "ABSENT"), (425, "mg/dL"), (483, "Absent"))
    row(110, (44, "URINARY BILIRUBIN"), (242, "Diazo coupling"), (363, "ABSENT"), (425, "mg/dL"), (483, "Absent"))
    row(125, (44, "BILE PIGMENT"), (242, "Ehrlich reaction"), (363, "ABSENT"), (425, "-"), (483, "Absent"))
    row(140, (44, "Remarks"), (363, "Normal"))
    row(155, (44, "EPITHELIAL CELLS"), (242, "Microscopy"), (363, "1"), (425, "cells/HPF"), (483, "0-5"))
    c.showPage()
    c.save()
    return buf.getvalue()


def test_every_result_is_read_once_under_the_right_test(sessions: sessionmaker[Session], tmp_path: Path,
                                                         catalogue: CatalogueData) -> None:
    storage = LocalVolumeStorage(tmp_path / "uploads")
    with sessions.begin() as s:
        profile = make_profile(s)
        report = ingest_report(s, storage, profile_id=profile.id, uploaded_by=profile.owner_user_id, data=_report())
    assert Worker(sessions, [ExtractionStage(storage, catalogue)]).run_once()

    with sessions() as s:
        codes = {t.id: t.code for t in s.scalars(select(LabTest))}
        rows = s.scalars(select(Observation).where(Observation.report_id == report.id)).all()
        got = sorted((codes.get(o.test_id), o.raw_value) for o in rows)
    assert got == sorted([
        ("chol_total", "204"), ("hdl", "34"), ("ldl", "131"), ("tg_hdl_ratio", "3.17"), ("ldl_hdl_ratio", "3.9"),
        ("urine_colour", "Yellow"), ("urine_protein", "ABSENT"), ("urine_bilirubin", "ABSENT"),
        ("urine_epi", "1"),
    ])
