"""Parse visual lines into result rows: name · value · unit · reference range · flag.

The parser is layout-agnostic: it classifies each horizontal segment of a line
(value, unit, range, flag, name) rather than relying on fixed columns, so it
handles tabular, boxed and dotted-leader reports alike. Lines that do not look
like results (headers, patient details, notes) are dropped.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app.catalogue.units import normalize_unit
from app.extraction.layout import Line, Segment
from app.extraction.types import ParsedRow

NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?|\.\d+"
_VALUE = re.compile(rf"^(?P<q>[<>]=?)?\s*(?P<v>{NUM})\s*(?:\(?\s*(?P<f>H|L|HIGH|LOW)\s*\)?|\*)?$", re.I)
# value then unit: separated by a space ("6.50 10^3/µL") or glued when the unit starts with a letter ("13.9g/dL")
_VALUE_REST = re.compile(rf"^(?P<q>[<>]=?)?\s*(?P<v>{NUM})(?:\s+(?P<rest>\S.*)|(?P<glued>[^\d\s,.].*))$")
_FLAG = re.compile(r"^\(?\s*(H|L|HIGH|LOW|\*)\s*\)?$", re.I)
_PREFIX = r"(?:\[\s*)?(?:(?:desirable|normal|optimal|ref(?:erence)?)\s*:?\s*)?"
_SUFFIX = r"\s*\]?"
_RANGE_TWO = re.compile(rf"^{_PREFIX}(?P<lo>{NUM})\s*(?:-|–|—|to)\s*(?P<hi>{NUM}){_SUFFIX}$", re.I)
_RANGE_UPPER = re.compile(rf"^{_PREFIX}(?:<=?|≤|up\s*to|upto|less\s*than|below)\s*(?P<hi>{NUM}){_SUFFIX}$", re.I)
_RANGE_LOWER = re.compile(rf"^{_PREFIX}(?:>=?|≥|more\s*than|above|greater\s*than)\s*(?P<lo>{NUM}){_SUFFIX}$", re.I)
_LEADERS = re.compile(r"[.·…_]{3,}")
_LETTERS = re.compile(r"[A-Za-z]")

SECTION_KEYWORDS = [
    ("cbc", ("BLOOD COUNT", "CBC", "HAEMOGRAM", "HEMOGRAM", "HAEMATOLOGY", "HEMATOLOGY")),
    ("diabetes", ("DIABET", "GLUCOSE", "BLOOD SUGAR", "HBA1C", "GLYCATED")),
    ("lipid", ("LIPID",)),
    ("kidney", ("KIDNEY", "RENAL", "KFT", "RFT")),
    ("electrolytes", ("ELECTROLYTE",)),
    ("liver", ("LIVER", "LFT", "HEPATIC")),
    ("thyroid", ("THYROID",)),
    ("vitamins", ("VITAMIN",)),
    ("iron", ("IRON",)),
    ("inflammation", ("INFLAMMA", "C-REACTIVE")),
    ("urine", ("URINE", "URINALYSIS")),
    ("prostate", ("PROSTATE", "PSA")),
]


def to_decimal(text: str) -> Decimal | None:
    try:
        return Decimal(text.replace(",", ""))
    except InvalidOperation:
        return None


@dataclass(frozen=True)
class ParsedValue:
    raw: str
    value: Decimal
    qualifier: str | None
    flag: str | None
    unit: str | None = None


def parse_value(text: str, known_units: set[str]) -> ParsedValue | None:
    """A result value, optionally followed by a flag and/or a unit that OCR merged into the same box:
    "8,342", "2.11 (H)", "<0.5", "13.9g/dL", "15.2 gm/dL", "26.2 L ng/mL"."""
    s = text.strip()
    m = _VALUE.match(s)
    if m:
        value = to_decimal(m["v"])
        if value is None:
            return None
        return ParsedValue(m["v"], value, m["q"], _flag(m["f"]) if m["f"] else ("H" if s.endswith("*") else None))
    m = _VALUE_REST.match(s)
    if not m or (value := to_decimal(m["v"])) is None:
        return None
    rest = (m["rest"] or m["glued"]).split()
    flag = None
    if len(rest) > 1 and _FLAG.match(rest[0]):
        flag, rest = _flag(rest[0]), rest[1:]
    elif len(rest) > 1 and _FLAG.match(rest[-1]):
        flag, rest = _flag(rest[-1]), rest[:-1]
    unit = " ".join(rest)
    if normalize_unit(unit) in known_units:
        return ParsedValue(m["v"], value, m["q"], flag, unit)
    return None


def parse_range(text: str) -> tuple[Decimal | None, Decimal | None] | None:
    s = " ".join(text.split())
    if m := _RANGE_TWO.match(s):
        lo, hi = to_decimal(m["lo"]), to_decimal(m["hi"])
        if lo is not None and hi is not None and lo <= hi:
            return lo, hi
        return None
    if m := _RANGE_UPPER.match(s):
        return None, to_decimal(m["hi"])
    if m := _RANGE_LOWER.match(s):
        return to_decimal(m["lo"]), None
    return None


def _flag(text: str) -> str | None:
    t = text.strip("() ").upper()
    return {"H": "H", "HIGH": "H", "L": "L", "LOW": "L", "*": "H"}.get(t)


def detect_section(line: Line) -> str | None:
    text = line.text.strip()
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 3 or re.search(r"\d", text.replace("A1C", "")):
        return None
    upper_ratio = sum(c.isupper() for c in letters) / len(letters)
    if upper_ratio < 0.8 or len(line.segments) > 2:
        return None
    for code, keys in SECTION_KEYWORDS:
        if any(k in text.upper() for k in keys):
            return code
    return None


def _clean_name(parts: Iterable[str]) -> str:
    name = " ".join(p for p in parts if not re.fullmatch(r"[.·…_\s]+", p))
    name = _LEADERS.sub(" ", name)
    return " ".join(name.split()).strip(" :")


_TRAILING_VALUE = re.compile(rf"^(?P<name>.*[A-Za-z].*?)\s+(?P<value>(?:[<>]=?\s*)?(?:{NUM})(?:\s*\(?[HL]\)?)?)$")


def _split_trailing_values(segs: list[Segment], known_units: set[str]) -> list[Segment]:
    """A long name can overflow into the value cell ("… Concentration 33.8"); split the value off
    when the next segment is a unit or a range, so the row parses normally."""
    out: list[Segment] = []
    for i, seg in enumerate(segs):
        nxt = segs[i + 1].text.strip() if i + 1 < len(segs) else ""
        m = _TRAILING_VALUE.match(seg.text.strip())
        if m and nxt and (normalize_unit(nxt) in known_units or parse_range(nxt) is not None):
            out.append(Segment(m["name"], seg.x0, seg.x1, seg.tokens))
            out.append(Segment(m["value"], seg.x1, seg.x1, seg.tokens))
        else:
            out.append(seg)
    return out


def parse_line(line: Line, page: int, section: str | None, known_units: set[str]) -> ParsedRow | None:
    segs: list[Segment] = [s for s in line.segments if s.text.strip() and not re.fullmatch(r"[.·…_]+", s.text.strip())]
    segs = _split_trailing_values(segs, known_units)
    if len(segs) < 2:
        return _parse_single_segment(line, segs, page, section, known_units)

    # The value is the first segment after the name that parses as a number.
    value_idx, value = None, None
    for i in range(1, len(segs)):
        v = parse_value(segs[i].text, known_units)
        if v is not None:
            value_idx, value = i, v
            break
    if value is None or value_idx is None:
        return None
    name = _clean_name(s.text for s in segs[:value_idx])
    if not _LETTERS.search(name):  # "T3", "K+" and "pH" are valid names
        return None

    unit, rng_text, rng, flag = value.unit, None, None, value.flag
    for seg in segs[value_idx + 1:]:
        text = seg.text.strip()
        if flag is None and _FLAG.match(text):
            flag = _flag(text)
        elif unit is None and normalize_unit(text) in known_units and rng is None:
            unit = text
        elif rng is None and (r := parse_range(text)) is not None:
            rng_text, rng = text, r
        elif unit is None and rng is None and (split := _split_unit_range(text, known_units)):
            unit, rng_text, rng = split
    if unit is None and rng is None:
        return None
    return _row(name, value, unit, rng_text, rng, flag, segs, page, section)


def _split_unit_range(text: str, known_units: set[str]) -> tuple[str, str, tuple] | None:
    """OCR may merge the unit and range columns: 'mg/dL 70 - 100'."""
    m = re.match(rf"^(?P<u>\S+(?:\s\S+)?)\s+(?P<r>.*(?:{NUM}).*)$", text)
    if m and normalize_unit(m["u"]) in known_units and (r := parse_range(m["r"])) is not None:
        return m["u"], m["r"], r
    return None


def _parse_single_segment(line: Line, segs: list[Segment], page: int, section: str | None,
                          known_units: set[str]) -> ParsedRow | None:
    """Whole row captured as one OCR segment: 'Haemoglobin 13.9 g/dL 13.0 - 17.0'."""
    if len(segs) != 1:
        return None
    text = _LEADERS.sub(" ", segs[0].text)
    m = re.match(rf"^(?P<name>[A-Za-z][^\d]*?)\s+(?P<rest>(?:[<>]=?\s*)?(?:{NUM}).*)$", text)
    if not m:
        return None
    parts = m["rest"].split()
    value = parse_value(parts[0], known_units)
    if value is None:
        return None
    rest = " ".join(parts[1:])
    unit, rng_text, rng, flag = None, None, None, value.flag
    if rest:
        tokens = rest.split()
        if tokens and _FLAG.match(tokens[0]):
            flag, tokens = _flag(tokens[0]), tokens[1:]
        if tokens and normalize_unit(tokens[0]) in known_units:
            unit, tokens = tokens[0], tokens[1:]
        if tokens and (r := parse_range(" ".join(tokens))) is not None:
            rng_text, rng = " ".join(tokens), r
    if unit is None and rng is None:
        return None
    return _row(_clean_name([m["name"]]), value, unit, rng_text, rng, flag, segs, page, section)


def _row(name: str, value: ParsedValue, unit: str | None, rng_text: str | None, rng: tuple | None,
         flag: str | None, segs: list[Segment], page: int, section: str | None) -> ParsedRow:
    toks = [t for s in segs for t in s.tokens]
    return ParsedRow(
        raw_name=name, raw_value=value.raw, value=value.value, raw_unit=unit, raw_range=rng_text,
        range_low=rng[0] if rng else None, range_high=rng[1] if rng else None, flag=flag,
        qualifier=value.qualifier, section=section, page=page,
        bbox=(min(t.x0 for t in toks), min(t.top for t in toks), max(t.x1 for t in toks), max(t.bottom for t in toks)),
        confidence=min(t.conf for t in toks),
    )
