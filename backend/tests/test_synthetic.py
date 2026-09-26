import json
from decimal import Decimal
from pathlib import Path

import pytest
from pypdf import PdfReader

from app.catalogue import CatalogueData
from tools.synthetic.__main__ import generate
from tools.synthetic.values import egfr_ckd_epi_2021


@pytest.fixture(scope="module")
def generated(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, list[dict]]:
    out = tmp_path_factory.mktemp("synthetic")
    manifest = generate(out, count=12, histories=2, visits=3, seed=7)
    return out, manifest


def _truths(out: Path) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(out.glob("*.json"))]


def test_every_report_has_a_pdf_and_ground_truth(generated: tuple[Path, list[dict]]) -> None:
    out, manifest = generated
    assert len(manifest) == 12 + 2 * 3
    for m in manifest:
        assert (out / f"{m['id']}.pdf").stat().st_size > 1000
        assert (out / f"{m['id']}.json").exists()


def test_all_layouts_and_unit_styles_appear(generated: tuple[Path, list[dict]]) -> None:
    _, manifest = generated
    assert {m["layout"] for m in manifest} == {"table", "boxed", "leaders"}
    assert {m["unit_style"] for m in manifest} == {"conventional", "international", "si"}


def test_flags_match_the_printed_range(generated: tuple[Path, list[dict]]) -> None:
    out, _ = generated
    for truth in _truths(out):
        for r in truth["rows"]:
            v = Decimal(r["value_canonical"])
            high = Decimal(r["ref_high"]) if r["ref_high"] else None
            low = Decimal(r["ref_low"]) if r["ref_low"] else None
            expected = "H" if high is not None and v > high else "L" if low is not None and v < low else ""
            assert r["flag"] == expected, (truth["id"], r["test_code"])


def test_values_are_plausible(generated: tuple[Path, list[dict]], catalogue: CatalogueData) -> None:
    out, _ = generated
    for truth in _truths(out):
        for r in truth["rows"]:
            t = catalogue.test(r["test_code"])
            assert t.plausible_min <= Decimal(r["value_canonical"]) <= t.plausible_max, r


def test_printed_values_appear_in_the_pdf_text(generated: tuple[Path, list[dict]]) -> None:
    out, _ = generated
    for truth in _truths(out)[:6]:
        text = "".join(page.extract_text() for page in PdfReader(out / f"{truth['id']}.pdf").pages)
        assert "SYNTHETIC REPORT" in text
        for r in truth["rows"]:
            assert r["printed_value"] in text, (truth["id"], r["test_code"], r["printed_value"])


def test_bounding_boxes_lie_on_the_page(generated: tuple[Path, list[dict]]) -> None:
    out, _ = generated
    for truth in _truths(out):
        w, h = truth["page_size_pt"]
        for r in truth["rows"]:
            x0, top, x1, bottom = r["bbox"]
            assert 0 <= x0 < x1 <= w and 0 <= top < bottom <= h
            assert 0 <= r["page"] < truth["pages"]


def test_history_reports_carry_the_planted_trend(generated: tuple[Path, list[dict]]) -> None:
    out, _ = generated
    history = [t for t in _truths(out) if "person_id" in t]
    assert len(history) == 6
    by_person: dict[str, list[dict]] = {}
    for t in history:
        by_person.setdefault(t["person_id"], []).append(t)
    for visits in by_person.values():
        assert len({v["planted_trend"]["test_code"] for v in visits}) == 1
        assert sorted(v["collected_at"] for v in visits) == [v["collected_at"] for v in
                                                              sorted(visits, key=lambda v: v["visit"])]


def test_egfr_ckd_epi_2021() -> None:
    # Creatinine 1.0 mg/dL at age 50: 142 × (1/0.9)^-1.2 × 0.9938^50 ≈ 91.7 for a man;
    # 142 × (1/0.7)^-1.2 × 0.9938^50 × 1.012 ≈ 68.7 for a woman.
    assert round(egfr_ckd_epi_2021(1.0, 50, "male")) == 92
    assert round(egfr_ckd_epi_2021(1.0, 50, "female")) == 69
    # Below kappa the alpha exponent applies: lower creatinine gives a higher eGFR.
    assert egfr_ckd_epi_2021(0.6, 50, "male") > egfr_ckd_epi_2021(0.8, 50, "male") > 91
