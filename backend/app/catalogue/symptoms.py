"""Symptoms that can go along with an out-of-range result (data/catalogue/symptoms.csv, from NLM MedlinePlus).

Used by the explanation: the template names them directly, and the model receives them in its data so it names only
these. Wording is always "can go along with", never "you have".
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.config import settings

KINDS = {"symptoms", "often_none", "none"}
LANGS = ("en", "hi", "or")


@dataclass(frozen=True)
class Symptoms:
    kind: str  # symptoms | often_none | none
    names: dict[str, tuple[str, ...]]  # language -> symptom names
    source: str

    def for_language(self, language: str) -> tuple[str, ...]:
        return self.names.get(language) or self.names["en"]


def read_symptoms(path: Path, known_tests: set[str] | None = None) -> dict[tuple[str, str], Symptoms]:
    table: dict[tuple[str, str], Symptoms] = {}
    errors: list[str] = []
    with path.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            key = (r["test_code"], r["direction"])
            names = {lang: tuple(s.strip() for s in r[f"symptoms_{lang}"].split("|") if s.strip()) for lang in LANGS}
            if known_tests is not None and r["test_code"] not in known_tests:
                errors.append(f"symptoms for unknown test {r['test_code']!r}")
            if r["direction"] not in ("low", "high") or r["kind"] not in KINDS:
                errors.append(f"{key}: bad direction or kind")
            if (r["kind"] == "none") != (not names["en"]):
                errors.append(f"{key}: kind {r['kind']!r} does not match the symptom list")
            if names["en"] and any(len(names[lang]) != len(names["en"]) for lang in ("hi", "or") if names[lang]):
                errors.append(f"{key}: translations don't match the English list")
            if key in table:
                errors.append(f"{key}: duplicate")
            table[key] = Symptoms(r["kind"], names, r["source"])
    if errors:
        raise ValueError("symptoms.csv has problems:\n  " + "\n  ".join(errors))
    return table


@lru_cache(maxsize=1)
def symptom_table() -> dict[tuple[str, str], Symptoms]:
    path = Path(settings.data_dir) / "catalogue" / "symptoms.csv"
    return read_symptoms(path) if path.exists() else {}


def symptoms_for(test_code: str, status: str) -> Symptoms | None:
    """Symptoms for an out-of-range status (low, high, critical_low, critical_high); None when in range or unknown."""
    direction = "low" if status.endswith("low") else "high" if status.endswith("high") else None
    return symptom_table().get((test_code, direction)) if direction else None
