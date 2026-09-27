"""Unit normalisation.

Indian lab reports spell the same unit many ways ("gm/dl", "gm%", "lakhs/cumm",
"x10³/µL"…). `normalize_unit` maps a printed unit to a small set of keys so that
conversion lookups are exact. Conversions themselves live in the catalogue
(data/catalogue/unit_conversions.csv).
"""

import re

_SUPERSCRIPTS = {"³": "^3", "⁶": "^6", "⁹": "^9", "¹²": "^12", "²": "2"}

# Cleaned spelling → normalised key. Keys that normalise to themselves are omitted.
_ALIASES: dict[str, str] = {
    # mass concentration
    "gm/dl": "g/dl", "gms/dl": "g/dl", "gm%": "g/dl", "g%": "g/dl", "gram/dl": "g/dl", "grams/dl": "g/dl",
    "gm/l": "g/l",
    "mg%": "mg/dl", "mgs/dl": "mg/dl", "mg/100ml": "mg/dl",
    "mcg/dl": "ug/dl", "microg/dl": "ug/dl",
    "mcg/l": "ug/l",
    # enzymes and hormones
    "iu/l": "u/l", "units/l": "u/l", "u/litre": "u/l",
    "miu/l": "uiu/ml", "mu/l": "uiu/ml", "uu/ml": "uiu/ml", "microiu/ml": "uiu/ml", "miu/ml": "uiu/ml",
    # haematology
    "femtolitre": "fl", "femtoliter": "fl", "cu.micron": "fl", "cumicron": "fl", "um^3": "fl", "um3": "fl",
    "picogram": "pg", "pg/cell": "pg",
    "mm/hr": "mm/h", "mm/1sthr": "mm/h", "mm/1sthour": "mm/h", "mminfirsthour": "mm/h", "mm/1hr": "mm/h",
    "mm/hour": "mm/h", "mm/1sth": "mm/h",
    "x10^3/ul": "10^3/ul", "10*3/ul": "10^3/ul", "10e3/ul": "10^3/ul", "thou/ul": "10^3/ul",
    "thou/cumm": "10^3/ul", "k/ul": "10^3/ul", "10^3/cumm": "10^3/ul", "x10^3/cumm": "10^3/ul",
    "10^9/l": "10^3/ul", "x10^9/l": "10^3/ul", "thousand/cumm": "10^3/ul", "thousands/cumm": "10^3/ul",
    "x10^6/ul": "10^6/ul", "10*6/ul": "10^6/ul", "million/cumm": "10^6/ul", "millions/cumm": "10^6/ul",
    "mill/cumm": "10^6/ul", "million/ul": "10^6/ul", "mil/ul": "10^6/ul", "10^6/cumm": "10^6/ul",
    "x10^6/cumm": "10^6/ul", "10^12/l": "10^6/ul", "x10^12/l": "10^6/ul", "m/ul": "10^6/ul",
    "lakh/cumm": "lakh/ul", "lakhs/cumm": "lakh/ul", "lakhs/ul": "lakh/ul", "lac/cumm": "lakh/ul",
    "lacs/cumm": "lakh/ul", "lakh/mm3": "lakh/ul", "lakhs/mm3": "lakh/ul",
    "/cumm": "/ul", "cells/cumm": "/ul", "cells/ul": "/ul", "/mm3": "/ul", "cells/mm3": "/ul",
    "/c.mm": "/ul", "/cu.mm": "/ul", "/cmm": "/ul", "percumm": "/ul",
    # OCR reads superscripts as plain digits: "x10³/µL" → "x103/µL"
    "x103/ul": "10^3/ul", "103/ul": "10^3/ul", "x109/l": "10^3/ul", "109/l": "10^3/ul",
    "x106/ul": "10^6/ul", "106/ul": "10^6/ul", "x1012/l": "10^6/ul", "1012/l": "10^6/ul",
    # urine
    "cells/hpf": "/hpf", "perhpf": "/hpf", "/h.p.f": "/hpf", "/h.p.f.": "/hpf", "hpf": "/hpf", "/hpf.": "/hpf",
    "mg/gcreatinine": "mg/g", "mg/gcreat": "mg/g", "mg/gmcreatinine": "mg/g", "ug/mg": "mg/g",
    "ug/mgcreatinine": "mg/g", "mg/mmolcreatinine": "mg/mmol",
    # kidney function
    "ml/min/1.73m^2": "ml/min/1.73m2", "ml/min/1.73sq.m": "ml/min/1.73m2", "ml/min/1.73sqm": "ml/min/1.73m2",
    "ml/min/1.73sq.m.": "ml/min/1.73m2",
    # unitless
    "-": "", "ratio": "", "none": "", "nil": "",
    "percent": "%",
}


def normalize_unit(raw: str | None) -> str:
    """Return the normalised key for a printed unit ('' for unitless)."""
    if raw is None:
        return ""
    s = raw.strip().lower()
    for sup, rep in _SUPERSCRIPTS.items():
        s = s.replace(sup, rep)
    s = s.replace("µ", "u").replace("μ", "u").replace("×", "x")
    s = re.sub(r"\s+", "", s)
    s = s.rstrip(".") if s.endswith(".") and s not in _ALIASES else s
    # OCR confuses a final lowercase l with I or 1: "U/I", "mg/dI", "mg/d1". No real unit ends that way.
    s = re.sub(r"/(d?)[i1]$", r"/\1l", s)
    return _ALIASES.get(s, s)
