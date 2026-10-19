from decimal import Decimal

import pytest

from app.catalogue import CatalogueData
from app.extraction import known_unit_keys
from app.extraction.layout import group_lines
from app.extraction.parser import detect_section, parse_line, parse_range, parse_value
from app.extraction.types import Token


@pytest.fixture(scope="module")
def units(catalogue: CatalogueData) -> set[str]:
    return known_unit_keys(catalogue)


@pytest.mark.parametrize(
    ("text", "value", "flag", "unit", "qualifier"),
    [
        ("13.9", "13.9", None, None, None),
        ("8,342", "8342", None, None, None),
        ("2.11 (H)", "2.11", "H", None, None),
        ("112 H", "112", "H", None, None),
        ("4.2 L", "4.2", "L", None, None),
        ("<0.5", "0.5", None, None, "<"),
        ("13.9g/dL", "13.9", None, "g/dL", None),
        ("15.2 gm/dL", "15.2", None, "gm/dL", None),  # the final L is part of the unit, not a flag
        ("26.2 L ng/mL", "26.2", "L", "ng/mL", None),
        ("6.50 10^3/μL", "6.50", None, "10^3/μL", None),
        ("25 U/I", "25", None, "U/I", None),
    ],
)
def test_parse_value(units: set[str], text: str, value: str, flag: str | None, unit: str | None,
                     qualifier: str | None) -> None:
    v = parse_value(text, units)
    assert v is not None
    assert (v.value, v.flag, v.unit, v.qualifier) == (Decimal(value), flag, unit, qualifier)


@pytest.mark.parametrize("text", ["Haemoglobin", "mg/dL", "15.2 furlongs", "", "Page 1 of 2"])
def test_parse_value_rejects_non_values(units: set[str], text: str) -> None:
    assert parse_value(text, units) is None


@pytest.mark.parametrize(
    ("text", "low", "high"),
    [
        ("13.0 - 17.0", "13.0", "17.0"), ("13.0–17.0", "13.0", "17.0"), ("13.0 to 17.0", "13.0", "17.0"),
        ("67to 110", "67", "110"), ("[4.09-10.21]", "4.09", "10.21"), ("4,000 - 11,000", "4000", "11000"),
        ("< 200", None, "200"), ("Up to 40", None, "40"), ("<5.0", None, "5.0"), ("Desirable: < 200", None, "200"),
        ("[Desirable: <5.0]", None, "5.0"), ("> 40", "40", None), (">= 89", "89", None),
    ],
)
def test_parse_range(text: str, low: str | None, high: str | None) -> None:
    assert parse_range(text) == (Decimal(low) if low else None, Decimal(high) if high else None)


@pytest.mark.parametrize("text", ["17.0 - 13.0", "mg/dL", "Negative", "1.033 to 1.011"])
def test_parse_range_rejects_non_ranges(text: str) -> None:
    assert parse_range(text) is None


def _line(*cells: tuple[str, float, float]):
    tokens = [Token(text, x0, 100, x1, 110) for text, x0, x1 in cells]
    lines = group_lines(tokens)
    assert len(lines) == 1
    return lines[0]


def test_table_row(units: set[str]) -> None:
    row = parse_line(_line(("Haemoglobin", 44, 110), ("13.9", 250, 266), ("g/dL", 340, 360), ("13.0 - 17.0", 440, 490)),
                     0, "cbc", units)
    assert row is not None
    assert (row.raw_name, row.value, row.raw_unit, row.range_low, row.range_high, row.flag) == (
        "Haemoglobin", Decimal("13.9"), "g/dL", Decimal("13.0"), Decimal("17.0"), None)
    assert row.section == "cbc"


def test_flag_column_and_thousands(units: set[str]) -> None:
    row = parse_line(_line(("Leukocyte Count", 44, 120), ("12,342", 250, 280), ("H", 312, 318),
                           ("/cumm", 340, 370), ("4000 to 10000", 440, 500)), 0, "cbc", units)
    assert row is not None and row.value == Decimal("12342") and row.flag == "H" and row.raw_unit == "/cumm"


def test_leaders_row(units: set[str]) -> None:
    row = parse_line(_line(("Fasting Plasma Glucose", 48, 150), ("...................", 152, 290),
                           ("112 H", 300, 340), ("mg/dL", 350, 380), ("[69 – 98]", 430, 470)), 0, None, units)
    assert row is not None
    assert (row.raw_name, row.value, row.flag, row.range_high) == ("Fasting Plasma Glucose", Decimal("112"), "H",
                                                                   Decimal("98"))


def test_name_overflowing_into_value_cell(units: set[str]) -> None:
    row = parse_line(_line(("Mean Corpuscular Haemoglobin Concentration 33.8", 44, 300), ("gm/dL", 324, 350),
                           ("31.4 to 34.5", 404, 450)), 0, "cbc", units)
    assert row is not None and row.raw_name == "Mean Corpuscular Haemoglobin Concentration"
    assert row.value == Decimal("33.8")


def test_unitless_row_needs_a_range(units: set[str]) -> None:
    assert parse_line(_line(("Specific Gravity", 44, 120), ("1.021", 250, 275), ("1.005 - 1.030", 440, 500)),
                      0, "urine", units) is not None
    assert parse_line(_line(("Age / Sex", 44, 100), ("45", 250, 260), ("Y / Female", 270, 330)), 0, None, units) is None


@pytest.mark.parametrize(
    ("text", "code"),
    [("COMPLETE BLOOD COUNT (CBC)", "cbc"), ("LIPID PROFILE", "lipid"), ("LIVER FUNCTION TEST (LFT)", "liver"),
     ("URINE ROUTINE EXAMINATION", "urine"), ("THYROID PROFILE", "thyroid"), ("Haemoglobin", None),
     ("COMPREHENSIVE HEALTH CHECK", None)],
)
def test_detect_section(text: str, code: str | None) -> None:
    assert detect_section(_line((text, 44, 300))) == code


def _row_line(*cells: tuple[str, float]):
    """One table row; each cell is (text, x0) and about 6 pt wide per character."""
    tokens = [Token(text, x0, 100, x0 + 6 * len(text), 110) for text, x0 in cells]
    return group_lines(tokens)[0]


@pytest.fixture(scope="module")
def columns():
    from app.extraction.parser import detect_columns
    header = _row_line(("TEST NAME", 45), ("METHODOLOGY", 241), ("VALUE", 362), ("UNITS", 427),
                       ("Bio. Ref. Interval.", 483))
    found = detect_columns(header)
    assert found is not None
    return found


def test_method_column_is_not_part_of_the_name(units: set[str], columns) -> None:
    row = parse_line(_row_line(("Neutrophils", 44), ("Percentage", 120), ("Flow Cytometry", 243), ("47.2", 362),
                               ("%", 425), ("40-80", 483)), 0, "cbc", units, columns)
    assert row is not None and row.raw_name == "Neutrophils Percentage" and row.value == Decimal("47.2")
    row = parse_line(_line(("Platelet to Large Cell", 44, 121), ("Ratio (PLCR)", 125, 170), ("Calculated", 242, 280),
                           ("27.6", 363, 379), ("%", 425, 432), ("19.7-42.4", 484, 517)), 0, "cbc", units, columns)
    assert row is not None and row.raw_name == "Platelet to Large Cell Ratio (PLCR)"


def test_method_word_without_a_header_is_dropped(units: set[str]) -> None:
    row = parse_line(_line(("TOTAL CHOLESTEROL", 45, 134), ("PH OTOMETRY", 264, 314), ("204", 374, 389),
                           ("mg/dL", 436, 463), ("< 200", 493, 516)), 0, "lipid", units)
    assert row is not None and row.raw_name == "TOTAL CHOLESTEROL"


@pytest.mark.parametrize(
    "cells",
    [
        [("DESIRABLE", 49, 100), ("<200", 150, 170), ("<100", 299, 320), ("NORMAL", 340, 380), ("<150", 400, 420)],
        [("BORDERLINE HIGH", 49, 120), ("200-239", 150, 190), ("HIGH", 209, 230), (">60", 250, 270)],
        [("Children: <=10 mm/hr", 44, 160)],
        [("Deficiency : <=20 ng/ml", 44, 160), ("Insufficiency : 21-29 ng/ml", 200, 330)],
    ],
)
def test_reference_table_rows_are_not_results(units: set[str], cells) -> None:
    assert parse_line(_line(*cells), 0, None, units) is None


def test_ranges_with_a_label_or_as_proportions(units: set[str]) -> None:
    assert parse_range("Adult : 17-43") == (Decimal("17"), Decimal("43"))
    assert parse_range("9:1-23:1") == (Decimal("9"), Decimal("23"))


def test_word_answer_row(units: set[str], columns) -> None:
    row = parse_line(_row_line(("URINA RY PROTEIN", 44), ("PEI", 242), ("ABSENT", 362), ("mg/dL", 425),
                               ("Absent", 483)), 0, "urine", units, columns)
    assert row is not None
    assert (row.raw_name, row.raw_value, row.value, row.raw_range) == ("URINA RY PROTEIN", "ABSENT", None, "Absent")


def test_test_lists_and_summaries_are_recognised() -> None:
    from app.extraction.parser import starts_summary
    assert detect_section(_line(("Tests Done : KIDPRO,LIPID PROFILE, LIVER FUNCTION TESTS", 44, 400))) is None
    assert starts_summary(_line(("Tests Outside Reference Range", 44, 200)))
    assert not starts_summary(_line(("Bio. Ref. Interval.", 44, 120)))
