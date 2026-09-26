from decimal import Decimal

import pytest

from app.catalogue import CatalogueData
from app.catalogue.convert import UnitConverter
from app.catalogue.units import normalize_unit


@pytest.mark.parametrize(
    ("printed", "key"),
    [
        ("gm/dL", "g/dl"), ("gm%", "g/dl"), ("g/dl", "g/dl"),
        ("mg%", "mg/dl"), ("MG/DL", "mg/dl"),
        ("lakhs/cumm", "lakh/ul"), ("Lakh/cumm", "lakh/ul"),
        ("/cumm", "/ul"), ("cells/cu.mm", "cells/cu.mm"),
        ("million/cumm", "10^6/ul"), ("x10⁶/µL", "10^6/ul"), ("10^12/L", "10^6/ul"),
        ("x10³/µL", "10^3/ul"), ("10³/µL", "10^3/ul"), ("10^9/L", "10^3/ul"), ("K/uL", "10^3/ul"),
        ("µIU/mL", "uiu/ml"), ("mIU/L", "uiu/ml"), ("uIU/ml", "uiu/ml"),
        ("IU/L", "u/l"), ("U/l", "u/l"),
        ("µmol/L", "umol/l"), ("μmol/L", "umol/l"),
        ("mm/1st hr", "mm/h"), ("mm/hr", "mm/h"),
        ("mL/min/1.73m²", "ml/min/1.73m2"), ("ml/min/1.73 m2", "ml/min/1.73m2"),
        ("cells/hpf", "/hpf"), ("/HPF", "/hpf"),
        ("mg/g creat", "mg/g"), ("mcg/dL", "ug/dl"),
        ("", ""), ("-", ""), ("ratio", ""), (None, ""),
    ],
)
def test_normalize_unit(printed: str | None, key: str) -> None:
    assert normalize_unit(printed) == key


@pytest.mark.parametrize(
    ("test", "value", "unit", "expected"),
    [
        ("glucose_fasting", "5.5", "mmol/L", "99.088"),
        ("hba1c", "48", "mmol/mol", "6.54304"),
        ("plt", "2.5", "lakhs/cumm", "250"),
        ("wbc", "7450", "/cumm", "7.45"),
        ("creatinine", "88.4", "µmol/L", "1.0000"),
        ("hb", "135", "g/L", "13.5"),
        ("sodium", "140", "mEq/L", "140"),
        ("tsh", "2.1", "mIU/L", "2.1"),
    ],
)
def test_to_canonical(catalogue: CatalogueData, test: str, value: str, unit: str, expected: str) -> None:
    got = UnitConverter(catalogue).to_canonical(test, Decimal(value), unit)
    assert got is not None
    assert abs(got - Decimal(expected)) < Decimal("0.001")


def test_unknown_unit_returns_none(catalogue: CatalogueData) -> None:
    conv = UnitConverter(catalogue)
    assert conv.to_canonical("hb", Decimal("13"), "mmol/mol") is None
    assert not conv.supports("hb", "furlongs")


def test_round_trip(catalogue: CatalogueData) -> None:
    conv = UnitConverter(catalogue)
    for c in catalogue.conversions:
        back = conv.to_canonical(c.test_code, conv.from_canonical(c.test_code, Decimal("12.34"), c.from_unit),
                                 c.from_unit)
        assert back is not None and abs(back - Decimal("12.34")) < Decimal("1e-9"), c
