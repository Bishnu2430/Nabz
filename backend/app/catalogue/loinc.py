"""LOINC code validation (mod-10 check digit, as specified in the LOINC Users' Guide)."""

import re

_LOINC = re.compile(r"^(\d{1,7})-(\d)$")


def check_digit(number: str) -> int:
    """Check digit for the numeric part of a LOINC code (equivalent to Luhn)."""
    digits = [int(c) for c in reversed(number)]
    total = 0
    for i, d in enumerate(digits):
        if i % 2 == 0:  # odd positions counted from the right are doubled
            d *= 2
            total += d // 10 + d % 10
        else:
            total += d
    return (10 - total % 10) % 10


def is_valid_loinc(code: str) -> bool:
    m = _LOINC.match(code)
    return bool(m) and check_digit(m.group(1)) == int(m.group(2))
