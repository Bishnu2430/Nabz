"""Turn sampled values into a printable report specification with ground truth."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.catalogue.convert import UnitConverter
from app.catalogue.data import CatalogueData
from tools.synthetic.values import Persona, round_to

PANEL_TITLES = {
    "cbc": "COMPLETE BLOOD COUNT (CBC)",
    "diabetes": "DIABETES PROFILE",
    "lipid": "LIPID PROFILE",
    "kidney": "KIDNEY FUNCTION TEST (KFT)",
    "electrolytes": "SERUM ELECTROLYTES",
    "liver": "LIVER FUNCTION TEST (LFT)",
    "thyroid": "THYROID PROFILE",
    "vitamins": "VITAMINS",
    "iron": "IRON STUDIES",
    "inflammation": "INFLAMMATION MARKERS",
    "urine": "URINE ROUTINE EXAMINATION",
    "prostate": "PROSTATE",
}

PANEL_TESTS = {
    "cbc": ["hb", "hct", "rbc", "wbc", "plt", "mcv", "mch", "mchc", "rdw", "neut_pct", "lymph_pct",
            "mono_pct", "eos_pct", "baso_pct", "esr"],
    "diabetes": ["glucose_fasting", "glucose_pp", "hba1c", "eag"],
    "lipid": ["chol_total", "tg", "hdl", "ldl", "vldl", "non_hdl", "chol_hdl_ratio"],
    "kidney": ["urea", "bun", "creatinine", "uric_acid", "egfr"],
    "electrolytes": ["sodium", "potassium", "chloride", "bicarbonate", "calcium", "phosphorus", "magnesium"],
    "liver": ["bili_total", "bili_direct", "bili_indirect", "alt", "ast", "alp", "ggt", "protein_total",
              "albumin", "globulin", "ag_ratio"],
    "thyroid": ["t3", "t4", "tsh"],
    "thyroid_free": ["ft3", "ft4", "tsh"],
    "vitamins": ["vitamin_d", "vitamin_b12", "folate"],
    "iron": ["iron", "tibc", "tsat", "ferritin"],
    "inflammation": ["crp"],
    "urine": ["urine_ph", "urine_sg", "urine_pus", "urine_rbc"],
    "urine_acr": ["urine_ph", "urine_sg", "urine_pus", "urine_rbc", "urine_acr"],
    "prostate": ["psa"],
}

PACKAGES = {
    "Comprehensive Health Check": ["cbc", "diabetes", "lipid", "kidney", "liver", "thyroid", "vitamins", "urine"],
    "Diabetes Care Profile": ["diabetes", "kidney", "lipid", "urine_acr"],
    "Anaemia Profile": ["cbc", "iron", "vitamins"],
    "Basic Health Check": ["cbc", "diabetes", "lipid"],
    "Liver and Kidney Profile": ["liver", "kidney", "electrolytes"],
    "Thyroid Profile": ["thyroid_free"],
    "Fever Panel": ["cbc", "inflammation", "urine"],
}

# Printed-unit spellings that normalise to the canonical unit.
SPELLINGS = {
    "g/dL": ["g/dL", "gm/dL", "g/dl", "gm%"],
    "mg/dL": ["mg/dL", "mg/dl", "mg%"],
    "U/L": ["U/L", "IU/L", "U/l"],
    "µIU/mL": ["µIU/mL", "uIU/ml", "mIU/L"],
    "10^3/µL": ["10^3/µL", "x10³/µL", "10³/µL"],
    "10^6/µL": ["10^6/µL", "x10^6/µL"],  # no superscript 6 in the standard PDF fonts
    "fL": ["fL", "fl"],
    "mm/h": ["mm/hr", "mm/1st hr", "mm/h"],
    "ng/mL": ["ng/mL", "ng/ml"],
    "pg/mL": ["pg/mL", "pg/ml"],
    "ng/dL": ["ng/dL", "ng/dl"],
    "µg/dL": ["µg/dL", "ug/dl", "mcg/dL"],
    "mg/L": ["mg/L", "mg/l"],
    "mmol/L": ["mmol/L", "mmol/l"],
    "mL/min/1.73m²": ["mL/min/1.73m²", "ml/min/1.73 m2"],
    "/hpf": ["/hpf", "cells/hpf", "/HPF"],
    "mg/g": ["mg/g", "mg/g creat"],
    "ratio": [""],
}
MONOVALENT = {"sodium", "potassium", "chloride", "bicarbonate"}

# Alternative printed units by lab style: test → (unit, decimals).
STYLE_UNITS = {
    "conventional": {"wbc": ("/cumm", 0), "plt": ("lakhs/cumm", 2), "rbc": ("million/cumm", 2)},
    "international": {},
    "si": {
        "glucose_fasting": ("mmol/L", 1), "glucose_pp": ("mmol/L", 1), "glucose_random": ("mmol/L", 1),
        "eag": ("mmol/L", 1), "hba1c": ("mmol/mol", 0), "chol_total": ("mmol/L", 2), "hdl": ("mmol/L", 2),
        "ldl": ("mmol/L", 2), "vldl": ("mmol/L", 2), "non_hdl": ("mmol/L", 2), "tg": ("mmol/L", 2),
        "creatinine": ("µmol/L", 0), "urea": ("mmol/L", 1), "uric_acid": ("µmol/L", 0),
        "bili_total": ("µmol/L", 1), "bili_direct": ("µmol/L", 1), "bili_indirect": ("µmol/L", 1),
        "calcium": ("mmol/L", 2), "vitamin_d": ("nmol/L", 0), "vitamin_b12": ("pmol/L", 0),
        "iron": ("µmol/L", 1), "tibc": ("µmol/L", 1), "ft4": ("pmol/L", 1), "ft3": ("pmol/L", 1),
    },
}


@dataclass
class Lab:
    name: str
    address: str
    doctor: str
    unit_style: str
    layout: str
    range_seed: int
    phone: str = ""
    email: str = ""
    tagline: str = "Pathology · Biochemistry · Haematology · Clinical Pathology"
    colour: str = "#1f5f8b"  # logo and rule colour
    technologist: str = ""
    referrer: str = "Self"  # printed as "Ref. By": the doctor who asked for the test
    collection_point: str = "Main Centre"


@dataclass
class Row:
    test_code: str
    printed_name: str
    printed_value: str
    printed_unit: str
    printed_range: str
    flag: str  # "H", "L" or ""
    value_canonical: Decimal
    ref_low: Decimal | None  # canonical units
    ref_high: Decimal | None
    page: int = 0
    bbox: tuple[float, float, float, float] = (0, 0, 0, 0)  # x0, top, x1, bottom in PDF points, top-left origin


@dataclass
class Section:
    panel: str
    title: str
    rows: list[Row] = field(default_factory=list)


@dataclass
class ReportSpec:
    id: str
    lab: Lab
    patient_name: str
    persona: Persona
    package: str
    collected_at: date
    lab_no: str
    sections: list[Section] = field(default_factory=list)


def _fmt(value: float, decimals: int, thousands: bool = False) -> str:
    v = round_to(value, decimals)
    s = f"{v:,.{decimals}f}" if thousands else f"{v:.{decimals}f}"
    return s


def _bound_to_printed(conv: UnitConverter, code: str, unit: str, decimals: int, x: float | None,
                      narrow: bool = False) -> float | None:
    """A canonical range bound as a lab would print it in `unit`.

    Labs print round bounds for large numbers: two significant figures from 1000 up (4000 – 10000), the nearest 5
    for three-digit bounds (< 200, 250 – 450). A narrow range keeps its exact bounds, or sodium's 135 – 145 would
    collapse to 140 – 140.
    """
    if x is None:
        return None
    p = conv.from_canonical(code, Decimal(str(x)), unit)
    if p is None:
        return None
    f = float(p)
    if abs(f) >= 1000:
        step = 10 ** (math.floor(math.log10(abs(f))) - 1)
        f = round(f / step) * step
    elif abs(f) >= 100 and not narrow:
        f = math.floor(f / 5 + 0.5) * 5
    return round_to(f, decimals)


def _bound_to_canonical(conv: UnitConverter, code: str, unit: str, p: float | None) -> Decimal | None:
    if p is None:
        return None
    c = conv.to_canonical(code, Decimal(str(p)), unit)
    return c.quantize(Decimal("0.0001")) if c is not None else None


def build_sections(values: dict[str, float], persona: Persona, package: str, lab: Lab,
                   cat: CatalogueData, conv: UnitConverter, rng: random.Random) -> list[Section]:
    lab_rng = random.Random(lab.range_seed)  # stable per lab: same ranges and spellings on every report
    sep = lab_rng.choice([" - ", " – ", "-", " to "])
    upper_fmt = lab_rng.choice(["< {h}", "Up to {h}", "<{h}"])
    lower_fmt = lab_rng.choice(["> {l}", ">= {l}"])
    spelling = {canon: lab_rng.choice(opts) for canon, opts in SPELLINGS.items()}
    jitter: dict[str, tuple[float, float]] = {}

    panels = list(PACKAGES[package])
    if persona.sex == "male" and persona.age >= 45 and package == "Comprehensive Health Check":
        panels.append("prostate")
    sections: list[Section] = []
    for panel in panels:
        base = "thyroid" if panel == "thyroid_free" else "urine" if panel == "urine_acr" else panel
        section = Section(base, PANEL_TITLES[base])
        for code in PANEL_TESTS[panel]:
            test = cat.test(code)
            unit_display, decimals = test.unit, test.decimals
            style_unit = STYLE_UNITS[lab.unit_style].get(code)
            if style_unit:
                unit_display, decimals = style_unit
                printed_unit = unit_display
            elif code in MONOVALENT and lab_rng.random() < 0.3:
                printed_unit = "mEq/L"
            else:
                printed_unit = spelling.get(test.unit, test.unit)

            canonical = min(max(values[code], float(test.plausible_min)), float(test.plausible_max))
            printed_num = conv.from_canonical(code, Decimal(str(canonical)), printed_unit)
            assert printed_num is not None, f"no conversion for {code} → {printed_unit}"
            printed_float = round_to(float(printed_num), decimals)
            value_canon = conv.to_canonical(code, Decimal(str(printed_float)), printed_unit)
            assert value_canon is not None

            # reference range: catalogue default for the persona's sex, jittered per lab
            rr = next((r for r in cat.ranges if r.test_code == code and r.sex == persona.sex),
                      next((r for r in cat.ranges if r.test_code == code and r.sex == "unknown"), None))
            if code not in jitter:
                jitter[code] = (lab_rng.uniform(-1, 1), lab_rng.uniform(-1, 1))
            lo = float(rr.low) if rr and rr.low is not None else None
            hi = float(rr.high) if rr and rr.high is not None else None
            # Labs differ slightly: shift each bound by up to 4 % of the range width (3 % of the
            # bound itself when the range is one-sided), so narrow ranges never invert.
            width = (hi - lo) if lo is not None and hi is not None else None
            if lo:  # a lower bound of 0 stays 0: labs print "0 - 39", never "-1 to 39"
                lo = max(lo + jitter[code][0] * (0.04 * width if width else 0.03 * lo), 0.0)
            if hi is not None:
                hi += jitter[code][1] * (0.04 * width if width else 0.03 * hi)

            narrow = bool(width and hi and width / hi < 0.2)
            plo = _bound_to_printed(conv, code, printed_unit, decimals, lo, narrow)
            phi = _bound_to_printed(conv, code, printed_unit, decimals, hi, narrow)
            if plo is not None and phi is not None:
                printed_range = f"{_fmt(plo, decimals)}{sep}{_fmt(phi, decimals)}"
            elif phi is not None:
                printed_range = upper_fmt.format(h=_fmt(phi, decimals))
                if base == "lipid" and lab_rng.random() < 0.3:
                    printed_range = "Desirable: " + printed_range
            elif plo is not None:
                printed_range = lower_fmt.format(l=_fmt(plo, decimals))
            else:
                printed_range = ""

            ref_low = _bound_to_canonical(conv, code, printed_unit, plo)
            ref_high = _bound_to_canonical(conv, code, printed_unit, phi)
            flag = ""
            if ref_high is not None and value_canon > ref_high:
                flag = "H"
            elif ref_low is not None and value_canon < ref_low:
                flag = "L"

            thousands = printed_unit == "/cumm" and lab_rng.random() < 0.6
            name = test.aliases[0] if rng.random() < 0.5 else rng.choice(test.aliases)
            section.rows.append(Row(
                test_code=code, printed_name=name, printed_value=_fmt(printed_float, decimals, thousands),
                printed_unit=printed_unit, printed_range=printed_range, flag=flag,
                value_canonical=value_canon.quantize(Decimal("0.0001")), ref_low=ref_low, ref_high=ref_high,
            ))
        sections.append(section)
    return sections
