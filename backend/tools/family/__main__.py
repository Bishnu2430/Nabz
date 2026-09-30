"""Load the Mohanty family (tools/family/story.py) into an account, the way a person would use Nabz.

    python -m tools.family --email dev@nabz.local [--replace]

Each lab report is generated with its ground truth, uploaded through the API (a PDF, or a phone photo of page 1),
read by the worker, checked against the truth (wrong or missing rows corrected, stray rows removed, as a person does
on the review screen), and confirmed. The worker then analyses and explains it. Imaging reports go in as other
records. `--replace` first deletes every person on the account (reports, files and all).
"""

from __future__ import annotations

import argparse
import dataclasses
import random
import re
import sys
import tempfile
import time
from datetime import date
from decimal import Decimal
from pathlib import Path

import cv2
import numpy as np
import pypdfium2 as pdfium
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api import deps
from app.catalogue import read_catalogue
from app.catalogue.convert import UnitConverter
from app.core.config import settings
from app.db import SessionLocal
from app.main import app
from app.models import AppUser
from tools.eval.extraction import degrade
from tools.family.story import CREDITS, FAMILY, IMAGING_CENTRES, LAB_DETAILS, Imaging, Person, Visit
from tools.synthetic.__main__ import LABS
from tools.synthetic.imaging import ImagingCentre, ImagingSpec, render_imaging_pdf
from tools.synthetic.render import render_pdf
from tools.synthetic.spec import Lab, ReportSpec, Row, build_sections
from tools.synthetic.values import HEALTHY, Persona, sample_baseline, sample_values

DONE = {"explaining", "explained"}
IMAGING_DIR = Path(settings.data_dir) / "imaging"


def age_on(dob: date, when: date) -> int:
    return when.year - dob.year - ((when.month, when.day) < (dob.month, dob.day))


class Family:
    def __init__(self, client: TestClient, seed: int):
        self.client = client
        self.cat = read_catalogue(Path(settings.data_dir) / "catalogue")
        self.conv = UnitConverter(self.cat)
        self.cv = {t.code: t.cv_i for t in self.cat.tests if t.cv_i}
        self.seed = seed
        self.labs = {name: Lab(name, addr, doctor="", unit_style=style, layout=layout, range_seed=i * 7919)
                     for i, (name, addr, layout, style) in enumerate(LABS)}
        pathologists = {"Anvaya Diagnostics": "Dr. Smita Pattnaik", "Mahanadi Clinical Laboratory": "Dr. Ashok Mishra",
                        "Sanjeevani Path Lab": "Dr. Lakshmi Narayan", "Prakriti Diagnostic Centre": "Dr. Ritu Agarwal",
                        "Nirmaya Health Labs": "Dr. Debashis Roy", "Kalinga Test House": "Dr. Manoj Kumar Swain"}
        for name, lab in self.labs.items():
            lab.doctor = pathologists[name]
            for key, value in LAB_DETAILS[name].items():
                setattr(lab, key, value)

    # -- values -------------------------------------------------------------------------------------------------
    def _inside(self, code: str, sex: str, value: float) -> float:
        """Keep a value the story doesn't mention inside the middle of its range, so it isn't flagged by chance."""
        rr = next((r for r in self.cat.ranges if r.test_code == code and r.sex == sex),
                  next((r for r in self.cat.ranges if r.test_code == code and r.sex == "unknown"), None))
        if rr is None:
            return value
        lo = float(rr.low) if rr.low is not None else None
        hi = float(rr.high) if rr.high is not None else None
        if lo is not None and hi is not None:
            mid, half = (lo + hi) / 2, (hi - lo) / 2
            return min(max(value, mid - 0.55 * half), mid + 0.55 * half)
        if hi is not None:
            return min(value, hi * 0.85)
        if lo is not None:
            return max(value, lo * 1.15)
        return value

    def values(self, person: Person, visit: Visit, baseline: dict[str, float], rng: random.Random) -> dict[str, float]:
        persona = Persona(person.sex, age_on(person.dob, visit.when), list(visit.conditions))
        base = {code: (visit.set[code] if code in visit.set else self._inside(code, person.sex, x))
                for code, x in baseline.items()}
        cv = {**self.cv, **{code: 0.0 for code in visit.set}}
        values = sample_values(persona, rng, baseline=base, cv={k: min(v, 2.5) for k, v in cv.items()})
        for code in visit.set:
            values[code] = visit.set[code]
        return values

    # -- reports ------------------------------------------------------------------------------------------------
    def spec(self, person: Person, visit: Visit, values: dict[str, float], rng: random.Random) -> ReportSpec:
        lab = dataclasses.replace(self.labs[visit.lab], referrer=visit.referrer or person.doctor,
                                  collection_point=person.collection_point)
        persona = Persona(person.sex, age_on(person.dob, visit.when), list(visit.conditions))
        lab_no = f"{visit.when:%y%m}{rng.randint(10000, 99999)}"
        spec = ReportSpec(id=lab_no, lab=lab, patient_name=person.name, persona=persona, package=visit.package,
                          collected_at=visit.when, lab_no=lab_no)
        spec.sections = build_sections(values, persona, visit.package, lab, self.cat, self.conv, rng)
        return spec

    @staticmethod
    def photo(pdf_path: Path, rng: random.Random) -> bytes | None:
        """Page 1 as a phone photo, or None when the report has more than one page."""
        pdf = pdfium.PdfDocument(str(pdf_path))
        try:
            if len(pdf) != 1:
                return None
            image = pdf[0].render(scale=200 / 72).to_numpy()
        finally:
            pdf.close()
        ok, buf = cv2.imencode(".jpg", degrade(np.ascontiguousarray(image[:, :, :3]), rng),
                               [cv2.IMWRITE_JPEG_QUALITY, 82])
        return buf.tobytes() if ok else None

    def wait(self, report_id: str, statuses: set[str], timeout: float = 180) -> dict:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            report = self.client.get(f"/v1/reports/{report_id}").json()
            if report["status"] in statuses:
                return report
            if report["status"] in ("failed", "rejected"):
                raise RuntimeError(f"report {report_id} {report['status']}")
            time.sleep(0.5)
        raise TimeoutError(f"report {report_id} still {report['status']}")

    def review(self, report: dict, truth: list[Row]) -> tuple[int, int, int]:
        """Correct the rows the reader got wrong, add the ones it missed, remove the ones that aren't results."""
        c = self.client
        squash = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())  # noqa: E731
        obs = list(report["observations"])
        fixed = added = removed = 0
        used: set[str] = set()
        for row in truth:
            want = Decimal(row.value_canonical)
            match = next((o for o in obs if o["id"] not in used and o["test_code"] == row.test_code), None)
            if match is None:
                match = next((o for o in obs if o["id"] not in used and o["test_code"] is None
                              and squash(o["raw_name"]) == squash(row.printed_name)), None)
            fields = {"raw_value": row.printed_value, "raw_unit": row.printed_unit or None,
                      "raw_range": row.printed_range or None}
            if match is None:
                r = c.post(f"/v1/reports/{report['id']}/observations",
                           json={"test_code": row.test_code, **{k: v for k, v in fields.items() if v}})
                assert r.status_code == 201, r.text
                added += 1
                continue
            used.add(match["id"])
            def close(got: object, expected: Decimal | None) -> bool:
                if got is None or expected is None:
                    return got is None and expected is None
                return abs(Decimal(str(got)) - expected) <= abs(expected) * Decimal("0.005") + Decimal("0.0001")

            right = (match["test_code"] == row.test_code and close(match["value"], want)
                     and close(match["ref_low"], row.ref_low) and close(match["ref_high"], row.ref_high))
            if not right:
                r = c.patch(f"/v1/observations/{match['id']}", json={"test_code": row.test_code, **fields})
                assert r.status_code == 200, r.text
                fixed += 1
        for o in obs:
            if o["id"] not in used:
                assert c.delete(f"/v1/observations/{o['id']}").status_code == 204
                removed += 1
        return fixed, added, removed

    def lab_report(self, pid: str, person: Person, visit: Visit, baseline: dict[str, float], out: Path) -> str:
        rng = random.Random(f"{self.seed}:{person.name}:{visit.when}")
        spec = self.spec(person, visit, self.values(person, visit, baseline, rng), rng)
        pdf = out / f"{spec.id}.pdf"
        pages = render_pdf(spec, pdf)
        data = self.photo(pdf, rng) if visit.photo else None
        kind = "photo" if data else "pdf"
        data = data or pdf.read_bytes()
        name = f"IMG_{visit.when:%Y%m%d}_{rng.randint(100000, 999999)}.jpg" if kind == "photo" else pdf.name
        r = self.client.post(f"/v1/profiles/{pid}/reports", files={"file": (name, data, "image/jpeg" if kind ==
                                                                              "photo" else "application/pdf")})
        assert r.status_code == 202, r.text
        rid = r.json()["report_id"]
        report = self.wait(rid, {"needs_review"})
        truth = [row for s in spec.sections for row in s.rows]
        fixed, added, removed = self.review(report, truth)
        r = self.client.post(f"/v1/reports/{rid}/confirm", json={"collected_at": visit.when.isoformat()})
        assert r.status_code == 202, r.text
        if visit.note:
            self.client.patch(f"/v1/reports/{rid}", json={"note": visit.note})
        self.wait(rid, DONE)
        flags = sum(1 for row in truth if row.flag)
        print(f"  {visit.when}  {visit.lab:<28} {visit.package:<28} {kind:<5} {pages}p  {len(truth):>2} rows, "
              f"{flags} flagged · review: {fixed} fixed, {added} added, {removed} removed")
        return rid

    def imaging(self, pid: str, person: Person, study: Imaging, out: Path) -> None:
        rng = random.Random(f"{self.seed}:{person.name}:{study.when}:img")
        centre = ImagingCentre(study.centre, **IMAGING_CENTRES[study.centre])
        study_no = f"RAD{study.when:%y%m}{rng.randint(1000, 9999)}"
        spec = ImagingSpec(centre=centre, patient_name=person.name, age=age_on(person.dob, study.when), sex=person.sex,
                           referrer=person.doctor, when=study.when, study_no=study_no,
                           title=study.title, history=study.history, technique=study.technique,
                           findings=study.findings, impression=study.impression, image=IMAGING_DIR / study.image,
                           credit=CREDITS[study.image])
        pdf = out / f"{spec.study_no}.pdf"
        render_imaging_pdf(spec, pdf)
        r = self.client.post(f"/v1/profiles/{pid}/records",
                             data={"kind": study.kind, "title": study.record_title or study.title.title(),
                                   "record_date": study.when.isoformat(), "facility": study.centre,
                                   **({"notes": study.notes} if study.notes else {})},
                             files={"file": (pdf.name, pdf.read_bytes(), "application/pdf")})
        assert r.status_code == 201, r.text
        print(f"  {study.when}  {study.centre:<28} {study.record_title or study.title}")


def main() -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.family")
    ap.add_argument("--email", required=True, help="the account to load the family into")
    ap.add_argument("--replace", action="store_true", help="delete every person on the account first")
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args()

    with SessionLocal() as s:
        user = s.scalar(select(AppUser).where(AppUser.email == a.email.lower()))
    if user is None or user.email_verified_at is None:
        print(f"{a.email}: no confirmed account", file=sys.stderr)
        return 1
    app.dependency_overrides[deps.current_user] = lambda: user
    with TestClient(app) as client, tempfile.TemporaryDirectory() as tmp:
        if a.replace:
            for p in client.get("/v1/profiles").json():
                assert client.delete(f"/v1/profiles/{p['id']}").status_code == 204
                print(f"deleted {p['display_name']}")
        fam = Family(client, a.seed)
        existing = {p["display_name"] for p in client.get("/v1/profiles").json()}
        for person in FAMILY:
            if person.name in existing:
                print(f"{person.name} is already on the account; skipped (use --replace)")
                continue
            r = client.post("/v1/profiles", json={
                "display_name": person.name, "sex": person.sex, "date_of_birth": person.dob.isoformat(),
                "relationship": person.relationship, "preferred_language": person.language,
                "consent_processing": True})
            assert r.status_code == 201, r.text
            pid = r.json()["id"]
            print(f"{person.name} ({person.relationship}, {len(person.visits)} lab reports, "
                  f"{len(person.imaging)} imaging)")
            rng = random.Random(f"{a.seed}:{person.name}")
            baseline = sample_baseline(Persona(person.sex, age_on(person.dob, date(2024, 1, 1))), rng)
            baseline = {code: x for code, x in baseline.items() if code in HEALTHY}
            events: list[tuple[date, object]] = [(v.when, v) for v in person.visits]
            events += [(i.when, i) for i in person.imaging]
            for _, event in sorted(events, key=lambda e: e[0]):
                if isinstance(event, Visit):
                    fam.lab_report(pid, person, event, baseline, Path(tmp))
                else:
                    fam.imaging(pid, person, event, Path(tmp))
    app.dependency_overrides.clear()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
