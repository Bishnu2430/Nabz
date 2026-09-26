"""Clinically consistent synthetic lab values for a persona.

Values are sampled in each test's canonical unit, then derived tests are
computed from their inputs (Friedewald LDL, CKD-EPI 2021 eGFR, differential
summing to 100 %, …) so that reports look internally consistent.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

# (mean, sd) in canonical units; a pair of tuples means (male, female).
Normal = tuple[float, float]
HEALTHY: dict[str, Normal | tuple[Normal, Normal]] = {
    "hb": ((14.8, 1.0), (13.2, 0.9)),
    "rbc": ((5.0, 0.3), (4.4, 0.3)),
    "wbc": (7.0, 1.5),
    "plt": (260, 55),
    "rdw": (12.8, 0.6),
    "esr": ((8, 4), (12, 5)),
    "glucose_fasting": (88, 7),
    "glucose_pp": (115, 12),
    "glucose_random": (105, 12),
    "hba1c": (5.2, 0.25),
    "chol_total": (175, 20),
    "hdl": ((47, 6), (55, 7)),
    "tg": (115, 30),
    "creatinine": ((0.95, 0.12), (0.75, 0.1)),
    "urea": (28, 6),
    "uric_acid": ((5.4, 0.8), (4.3, 0.7)),
    "sodium": (140, 1.8),
    "potassium": (4.3, 0.3),
    "chloride": (102, 2),
    "bicarbonate": (25, 1.5),
    "calcium": (9.4, 0.3),
    "phosphorus": (3.5, 0.4),
    "magnesium": (2.1, 0.15),
    "bili_total": (0.7, 0.2),
    "bili_direct": (0.18, 0.05),
    "alt": ((28, 8), (20, 6)),
    "ast": ((25, 6), (21, 5)),
    "alp": (80, 18),
    "ggt": ((30, 9), (20, 6)),
    "protein_total": (7.2, 0.35),
    "albumin": (4.4, 0.25),
    "tsh": (2.0, 0.7),
    "ft4": (1.25, 0.15),
    "ft3": (3.1, 0.35),
    "t3": (125, 20),
    "t4": (8.5, 1.4),
    "vitamin_d": (32, 8),
    "vitamin_b12": (420, 120),
    "folate": (9, 3),
    "iron": ((110, 25), (90, 22)),
    "tibc": (320, 35),
    "ferritin": ((120, 45), (55, 25)),
    "crp": (1.5, 1.0),
    "hs_crp": (1.2, 0.7),
    "urine_ph": (6.0, 0.5),
    "urine_sg": (1.018, 0.005),
    "urine_rbc": (0.6, 0.6),
    "urine_pus": (1.8, 1.2),
    "urine_acr": (10, 6),
    "psa": (1.2, 0.6),
}

# Condition → uniform ranges that override the healthy value (canonical units).
CONDITIONS: dict[str, dict[str, tuple[float, float]]] = {
    "prediabetes": {"glucose_fasting": (101, 125), "glucose_pp": (141, 199), "hba1c": (5.7, 6.4)},
    "diabetes": {"glucose_fasting": (130, 220), "glucose_pp": (200, 320), "glucose_random": (180, 300),
                 "hba1c": (6.8, 9.5), "urine_acr": (20, 120)},
    "iron_deficiency": {"hb": (8.6, 11.4), "ferritin": (4, 12), "iron": (22, 45), "tibc": (400, 480),
                        "rbc": (3.6, 4.2), "rdw": (15.0, 18.5)},
    "fatty_liver": {"alt": (60, 140), "ast": (45, 90), "ggt": (60, 150), "tg": (180, 320)},
    "hypothyroid": {"tsh": (6.0, 15.0), "ft4": (0.6, 0.9), "t4": (3.5, 5.0)},
    "ckd_early": {"creatinine": (1.5, 2.2), "urea": (45, 70), "urine_acr": (40, 250), "potassium": (4.9, 5.6)},
    "vitamin_d_deficiency": {"vitamin_d": (8, 19)},
    "dyslipidaemia": {"chol_total": (220, 285), "hdl": (32, 39), "tg": (160, 260)},
    "b12_deficiency": {"vitamin_b12": (110, 190)},
    "infection": {"wbc": (11.5, 16.0), "crp": (12, 60), "esr": (30, 60)},
    "critical_potassium": {"potassium": (6.4, 7.0)},
}


# Visit-to-visit variation (%) for tests without biological-variation data in the catalogue.
DEFAULT_VISIT_CV = {"urine_sg": 0.2, "urine_ph": 3.0, "sodium": 0.6, "chloride": 1.2}


@dataclass
class Persona:
    sex: str  # "male" | "female"
    age: int
    conditions: list[str] = field(default_factory=list)


def random_persona(rng: random.Random) -> Persona:
    sex = rng.choice(["male", "female"])
    age = rng.randint(22, 78)
    pool = [c for c in CONDITIONS if c != "critical_potassium"]
    if rng.random() < 0.4:
        conditions: list[str] = []
    else:
        conditions = rng.sample(pool, k=rng.choice([1, 1, 2]))
    if rng.random() < 0.03:
        conditions.append("critical_potassium")
    if sex == "male" and "iron_deficiency" in conditions and rng.random() < 0.7:
        conditions.remove("iron_deficiency")
    return Persona(sex, age, conditions)


def egfr_ckd_epi_2021(creatinine: float, age: int, sex: str) -> float:
    """CKD-EPI 2021 (race-free) creatinine equation, mL/min/1.73 m²."""
    female = sex == "female"
    kappa, alpha = (0.7, -0.241) if female else (0.9, -0.302)
    ratio = creatinine / kappa
    value = 142 * min(ratio, 1) ** alpha * max(ratio, 1) ** -1.200 * 0.9938 ** age
    return value * (1.012 if female else 1.0)


def sample_baseline(p: Persona, rng: random.Random) -> dict[str, float]:
    """A person's underlying values for the primary (non-derived) tests."""
    v: dict[str, float] = {}
    for code, spec in HEALTHY.items():
        mean, sd = spec[0 if p.sex == "male" else 1] if isinstance(spec[0], tuple) else spec  # type: ignore[misc]
        v[code] = rng.gauss(mean, sd)
    for cond in p.conditions:
        for code, (lo, hi) in CONDITIONS[cond].items():
            v[code] = rng.uniform(lo, hi)
    return v


def sample_values(p: Persona, rng: random.Random, drift: dict[str, float] | None = None,
                  baseline: dict[str, float] | None = None, cv: dict[str, float] | None = None) -> dict[str, float]:
    """All test values (canonical units) for one report.

    Without `baseline` every primary value is freshly sampled. With a baseline
    (repeat visits of one person) each value varies around it by its
    within-subject CV (% in `cv`, default 4 %), and `drift` adds planted offsets.
    """
    if baseline is None:
        v = sample_baseline(p, rng)
    else:
        noise = {**DEFAULT_VISIT_CV, **(cv or {})}
        v = {code: x * (1 + rng.gauss(0, noise.get(code, 3.0) / 100)) for code, x in baseline.items()}
    for code, delta in (drift or {}).items():
        v[code] += delta

    # keep strictly positive where a negative value is impossible
    for code in list(v):
        if code not in ("urine_ph",):
            v[code] = max(v[code], 0.01)

    # derived haematology
    v["hct"] = v["hb"] * rng.uniform(2.9, 3.1)
    v["mcv"] = v["hct"] / v["rbc"] * 10
    v["mch"] = v["hb"] / v["rbc"] * 10
    v["mchc"] = v["hb"] / v["hct"] * 100
    diff = {"neut_pct": rng.gauss(58, 6), "lymph_pct": rng.gauss(32, 5), "mono_pct": rng.gauss(6, 1.5),
            "eos_pct": abs(rng.gauss(3, 1.2)), "baso_pct": abs(rng.gauss(0.5, 0.3))}
    if "infection" in p.conditions:
        diff["neut_pct"] += 14
    total = sum(diff.values())
    for k, x in diff.items():
        v[k] = x / total * 100

    # derived chemistry
    v["eag"] = 28.7 * v["hba1c"] - 46.7
    v["vldl"] = v["tg"] / 5
    v["ldl"] = max(v["chol_total"] - v["hdl"] - v["vldl"], 20)
    v["non_hdl"] = v["chol_total"] - v["hdl"]
    v["chol_hdl_ratio"] = v["chol_total"] / v["hdl"]
    v["bun"] = v["urea"] / 2.14
    v["egfr"] = egfr_ckd_epi_2021(v["creatinine"], p.age, p.sex)
    v["bili_direct"] = min(v["bili_direct"], v["bili_total"] * 0.6)
    v["bili_indirect"] = v["bili_total"] - v["bili_direct"]
    v["globulin"] = max(v["protein_total"] - v["albumin"], 1.5)
    v["ag_ratio"] = v["albumin"] / v["globulin"]
    v["tsat"] = v["iron"] / v["tibc"] * 100
    return v


def round_to(value: float, decimals: int) -> float:
    q = 10 ** decimals
    return math.floor(value * q + 0.5) / q
