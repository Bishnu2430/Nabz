"""CLI for the synthetic report generator. See tools/synthetic/__init__.py."""

from __future__ import annotations

import argparse
import csv
import json
import random
from dataclasses import asdict
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from faker import Faker

from app.catalogue import read_catalogue
from app.catalogue.convert import UnitConverter
from app.core.config import settings
from tools.synthetic.render import render_pdf
from tools.synthetic.spec import PACKAGES, Lab, ReportSpec, build_sections
from tools.synthetic.values import Persona, random_persona, sample_baseline, sample_values

# Fictional laboratories. Each has a fixed layout and unit style so every combination appears.
LABS = [
    ("Anvaya Diagnostics", "Plot 12, Saheed Nagar, Bhubaneswar 751007", "table", "conventional"),
    ("Mahanadi Clinical Laboratory", "Link Road, Cuttack 753012", "boxed", "international"),
    ("Sanjeevani Path Lab", "MG Road, Bengaluru 560001", "leaders", "conventional"),
    ("Prakriti Diagnostic Centre", "Sector 18, Noida 201301", "table", "si"),
    ("Nirmaya Health Labs", "Salt Lake Sector V, Kolkata 700091", "boxed", "conventional"),
    ("Kalinga Test House", "Janpath, Bhubaneswar 751001", "leaders", "international"),
]

# Planted yearly drifts for history mode (canonical units per year).
DRIFTS = {"hba1c": 0.35, "creatinine": 0.12, "tsh": 1.1, "alt": 12.0, "hb": -0.5, "chol_total": 12.0}


def _json_default(o: object) -> object:
    if isinstance(o, Decimal):
        return str(o)
    if isinstance(o, date):
        return o.isoformat()
    raise TypeError(type(o))


def _labs(fake: Faker) -> list[Lab]:
    return [Lab(name, addr, f"Dr. {fake.name()}", style, layout, range_seed=i * 7919)
            for i, (name, addr, layout, style) in enumerate(LABS)]


def _write(spec: ReportSpec, out: Path, extra: dict) -> dict:
    pages = render_pdf(spec, out / f"{spec.id}.pdf")
    rows = [asdict(r) for s in spec.sections for r in s.rows]
    truth = {
        "id": spec.id, "synthetic": True, "layout": spec.lab.layout, "unit_style": spec.lab.unit_style,
        "lab": {"name": spec.lab.name, "doctor": spec.lab.doctor}, "patient_name": spec.patient_name,
        "persona": asdict(spec.persona), "package": spec.package, "collected_at": spec.collected_at,
        "lab_no": spec.lab_no, "pages": pages, "page_size_pt": [595.28, 841.89],
        "sections": [{"panel": s.panel, "title": s.title} for s in spec.sections],
        "rows": rows, **extra,
    }
    (out / f"{spec.id}.json").write_text(json.dumps(truth, indent=2, default=_json_default, ensure_ascii=False),
                                         encoding="utf-8")
    return {"id": spec.id, "layout": spec.lab.layout, "unit_style": spec.lab.unit_style, "package": spec.package,
            "sex": spec.persona.sex, "age": spec.persona.age, "conditions": "|".join(spec.persona.conditions),
            "collected_at": spec.collected_at.isoformat(), "pages": pages, "rows": len(rows),
            "person": extra.get("person_id", ""), "visit": extra.get("visit", "")}


def generate(out: Path, count: int, histories: int, visits: int, seed: int) -> list[dict]:
    out.mkdir(parents=True, exist_ok=True)
    cat = read_catalogue(Path(settings.data_dir) / "catalogue")
    conv = UnitConverter(cat)
    cv = {t.code: t.cv_i for t in cat.tests if t.cv_i}
    fake = Faker("en_IN")
    Faker.seed(seed)
    rng = random.Random(seed)
    labs = _labs(fake)
    manifest: list[dict] = []

    for i in range(count):
        persona = random_persona(rng)
        lab = labs[i % len(labs)]
        package = rng.choice(list(PACKAGES))
        values = sample_values(persona, rng)
        spec = ReportSpec(
            id=f"syn-{seed}-{i:04d}", lab=lab, patient_name=fake.name_male() if persona.sex == "male"
            else fake.name_female(), persona=persona, package=package,
            collected_at=date(2026, 8, 1) - timedelta(days=rng.randint(0, 900)),
            lab_no=f"{rng.randint(10, 99)}{rng.randint(100000, 999999)}",
        )
        spec.sections = build_sections(values, persona, package, lab, cat, conv, rng)
        manifest.append(_write(spec, out, {}))

    for h in range(histories):
        persona = random_persona(rng)
        persona.conditions = [c for c in persona.conditions if c != "critical_potassium"]
        test = rng.choice(list(DRIFTS))
        slope = DRIFTS[test]
        baseline = sample_baseline(persona, rng)
        name = fake.name_male() if persona.sex == "male" else fake.name_female()
        lab = labs[rng.randrange(len(labs))]
        start = date(2026, 8, 1) - timedelta(days=365 * (visits - 1) + rng.randint(0, 60))
        package = "Comprehensive Health Check"
        for k in range(visits):
            when = start + timedelta(days=365 * k + rng.randint(-30, 30))
            years = (when - start).days / 365.25
            values = sample_values(persona, rng, drift={test: slope * years}, baseline=baseline, cv=cv)
            spec = ReportSpec(
                id=f"hist-{seed}-{h:02d}-v{k}", lab=lab, patient_name=name,
                persona=Persona(persona.sex, persona.age - (visits - 1 - k), persona.conditions),
                package=package, collected_at=when, lab_no=f"{rng.randint(10, 99)}{rng.randint(100000, 999999)}",
            )
            spec.sections = build_sections(values, spec.persona, package, lab, cat, conv, rng)
            manifest.append(_write(spec, out, {"person_id": f"hist-{seed}-{h:02d}", "visit": k,
                                               "planted_trend": {"test_code": test, "slope_per_year": slope}}))

    with (out / "manifest.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(manifest[0]))
        writer.writeheader()
        writer.writerows(manifest)
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m tools.synthetic")
    ap.add_argument("--out", default=str(Path(settings.data_dir) / "synthetic" / "generated"))
    ap.add_argument("--count", type=int, default=50, help="independent reports")
    ap.add_argument("--histories", type=int, default=5, help="people with repeated reports")
    ap.add_argument("--visits", type=int, default=4, help="reports per history person")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    manifest = generate(Path(a.out), a.count, a.histories, a.visits, a.seed)
    rows = sum(int(m["rows"]) for m in manifest)
    print(f"wrote {len(manifest)} reports ({rows} result rows) to {a.out}")


if __name__ == "__main__":
    main()
