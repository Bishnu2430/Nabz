"""Write the two reports behind "try a sample report" in the first-run walkthrough (data/samples/).

    python -m tools.family.samples

They are ordinary generated reports of fictional people, one for a woman and one for a man, with a few results
outside their range so there is something to explain and nothing critical. The files are committed: the API serves
them without the generator's development dependencies.
"""

from __future__ import annotations

import random
from datetime import date
from pathlib import Path

from app.core.config import settings
from tools.family.__main__ import Family, age_on
from tools.family.story import Person, Visit
from tools.synthetic.render import render_pdf
from tools.synthetic.values import HEALTHY, Persona, sample_baseline

OUT = Path(settings.data_dir) / "samples"
WHEN = date(2026, 9, 14)
PEOPLE = {
    "female": Person(
        name="Meera Nair", sex="female", dob=date(1985, 2, 11), relationship="self", language="en",
        doctor="Dr. Sanjukta Rath", collection_point="Main Centre",
        visits=[Visit(WHEN, "Anvaya Diagnostics", "Comprehensive Health Check",
                      {"hb": 11.2, "rbc": 4.0, "rdw": 15.4, "vitamin_d": 17, "vitamin_b12": 310, "tsh": 3.1,
                       "chol_total": 214, "hdl": 51, "tg": 142, "hba1c": 5.4, "glucose_fasting": 91})]),
    "male": Person(
        name="Rohan Das", sex="male", dob=date(1982, 8, 3), relationship="self", language="en",
        doctor="Dr. Prakash Nayak", collection_point="Main Centre",
        visits=[Visit(WHEN, "Anvaya Diagnostics", "Comprehensive Health Check",
                      {"hba1c": 6.1, "glucose_fasting": 108, "chol_total": 226, "hdl": 38, "tg": 198,
                       "vitamin_d": 19, "creatinine": 0.98})]),
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    fam = Family(client=None, seed=2026)  # type: ignore[arg-type]  # nothing is uploaded here
    for sex, person in PEOPLE.items():
        visit = person.visits[0]
        rng = random.Random(f"sample:{sex}")
        baseline = sample_baseline(Persona(person.sex, age_on(person.dob, visit.when)), rng)
        baseline = {code: x for code, x in baseline.items() if code in HEALTHY}
        spec = fam.spec(person, visit, fam.values(person, visit, baseline, rng), rng)
        path = OUT / f"health-check-{sex}.pdf"
        pages = render_pdf(spec, path)
        rows = [row for s in spec.sections for row in s.rows]
        print(f"{path.name}: {pages} page(s), {len(rows)} rows, {sum(1 for r in rows if r.flag)} flagged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
