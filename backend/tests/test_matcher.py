from decimal import Decimal

import pytest

from app.catalogue import CatalogueData
from app.catalogue.convert import UnitConverter
from app.catalogue.matcher import CatalogueMatcher
from app.extraction.interpret import Interpreter, RawRow


@pytest.fixture(scope="module")
def matcher(catalogue: CatalogueData) -> CatalogueMatcher:
    return CatalogueMatcher(catalogue, UnitConverter(catalogue))


@pytest.fixture(scope="module")
def interp(catalogue: CatalogueData, matcher: CatalogueMatcher) -> Interpreter:
    return Interpreter(catalogue, matcher, UnitConverter(catalogue))


@pytest.mark.parametrize(
    ("name", "section", "unit", "code"),
    [
        ("Haemoglobin", "cbc", "g/dL", "hb"),
        ("MeanCorpuscularVolume", "cbc", "fL", "mcv"),  # OCR dropped the spaces
        ("S.Creatinine", "kidney", "mg/dL", "creatinine"),
        ("Serum Chloride", "electrolytes", "mmol/L", "chloride"),
        ("SGPT (ALT)", "liver", "U/L", "alt"),
        ("RBC", "cbc", "million/cumm", "rbc"),
        ("RBCs", "urine", "/hpf", "urine_rbc"),
        ("pH", "urine", "", "urine_ph"),
        ("Hemoglobn", "cbc", "g/dL", "hb"),  # OCR misspelling → fuzzy
        ("Tota1 Cholestero1", "lipid", "mg/dL", "chol_total"),  # l read as 1
    ],
)
def test_matches(matcher: CatalogueMatcher, name: str, section: str, unit: str, code: str) -> None:
    m = matcher.match(name, section, unit)
    assert m.test_code == code, m


def test_ambiguous_name_returns_candidates(matcher: CatalogueMatcher) -> None:
    m = matcher.match("Blood Glucose", "diabetes", "mg/dL")
    assert m.test_code is None and m.method == "none"
    assert {c for c, _ in m.candidates} <= {"glucose_fasting", "glucose_pp", "glucose_random", "eag"}


def test_unrelated_text_does_not_match(matcher: CatalogueMatcher) -> None:
    assert matcher.match("Mystery test", None, None).test_code is None
    assert matcher.match("", None, None).method == "none"


def test_resolver_breaks_ties(catalogue: CatalogueData) -> None:
    class PickFasting:
        def resolve(self, raw_name, section, raw_unit, candidates):
            return "glucose_fasting" if any(c == "glucose_fasting" for c, _ in candidates) else None

    m = CatalogueMatcher(catalogue, UnitConverter(catalogue), resolver=PickFasting()).match("Blood Glucose",
                                                                                          "diabetes", "mg/dL")
    assert (m.test_code, m.method) == ("glucose_fasting", "resolver")


def _row(name: str, value: str, unit: str | None, rng: str | None, flag: str | None = None, conf: float = 0.97,
         source: str = "ocr", section: str | None = None) -> RawRow:
    return RawRow(name, value, unit, rng, flag, section, conf, source)


def test_converts_value_and_printed_range(interp: Interpreter) -> None:
    it = interp.interpret(_row("FBS", "5.2", "mmol/L", "3.9 - 5.5", section="diabetes"))
    assert it.test_code == "glucose_fasting" and it.unit == "mg/dL"
    assert abs(it.value_num - Decimal("93.68")) < Decimal("0.01")
    assert it.ref_source == "report" and abs(it.ref_high - Decimal("99.09")) < Decimal("0.01")


def test_falls_back_to_catalogue_range_by_sex(interp: Interpreter) -> None:
    male = interp.interpret(_row("Haemoglobin", "13.1", "g/dL", None), sex="male", age=58)
    female = interp.interpret(_row("Haemoglobin", "13.1", "g/dL", None), sex="female", age=58)
    unknown = interp.interpret(_row("Haemoglobin", "13.1", "g/dL", None))
    assert (male.ref_source, male.ref_low) == ("catalogue", Decimal("13.0"))
    assert female.ref_low == Decimal("12.0")
    assert unknown.ref_source == "none"  # sex-specific range and sex unknown: don't guess


def test_misread_value_far_outside_its_range_is_suspicious(interp: Interpreter) -> None:
    good = interp.interpret(_row("FBS", "94", "mg/dL", "69 - 99", section="diabetes"))
    misread = interp.interpret(_row("FBS", "944", "mg/dL", "69 - 99", section="diabetes"))
    assert good.features["range_excess"] == 0 and good.features["flag_mismatch"] == 0
    assert misread.features["range_excess"] > 0.9 and misread.features["flag_mismatch"] == 1
    assert misread.confidence < good.confidence - 0.3


def test_flag_that_disagrees_with_the_value_is_suspicious(interp: Interpreter) -> None:
    it = interp.interpret(_row("Haemoglobin", "14.0", "g/dL", "13.0 - 17.0", flag="H"))
    assert it.features["flag_mismatch"] == 1


def test_unknown_unit_and_manual_mapping(interp: Interpreter) -> None:
    it = interp.interpret(_row("Haemoglobin", "14.0", "furlongs", "13.0 - 17.0"))
    assert not it.unit_ok and it.ref_source == "none"
    forced = interp.interpret(_row("Blood Glucose", "101", "mg/dL", "70 - 100"), test_code="glucose_fasting")
    assert (forced.test_code, forced.match.method) == ("glucose_fasting", "manual")
