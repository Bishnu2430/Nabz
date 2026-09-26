"""Convert values between a printed unit and a test's canonical unit."""

from decimal import Decimal

from app.catalogue.data import CatalogueData
from app.catalogue.units import normalize_unit


class UnitConverter:
    def __init__(self, data: CatalogueData):
        self._canonical = {t.code: normalize_unit(t.unit) for t in data.tests}
        self._factors = {(c.test_code, normalize_unit(c.from_unit)): (c.factor, c.offset) for c in data.conversions}

    def supports(self, test_code: str, unit: str) -> bool:
        key = normalize_unit(unit)
        return key == self._canonical[test_code] or (test_code, key) in self._factors

    def to_canonical(self, test_code: str, value: Decimal, unit: str) -> Decimal | None:
        """Value in the canonical unit, or None if the printed unit is unknown for this test."""
        key = normalize_unit(unit)
        if key == self._canonical[test_code]:
            return value
        conv = self._factors.get((test_code, key))
        if conv is None:
            return None
        factor, offset = conv
        return value * factor + offset

    def from_canonical(self, test_code: str, value: Decimal, unit: str) -> Decimal | None:
        key = normalize_unit(unit)
        if key == self._canonical[test_code]:
            return value
        conv = self._factors.get((test_code, key))
        if conv is None:
            return None
        factor, offset = conv
        return (value - offset) / factor
