import pytest

from app.catalogue.loinc import check_digit, is_valid_loinc


@pytest.mark.parametrize("code", ["718-7", "4548-4", "2160-0", "62238-1", "13945-1", "9318-7", "62292-8"])
def test_known_codes_are_valid(code: str) -> None:
    assert is_valid_loinc(code)


@pytest.mark.parametrize("code", ["718-8", "4548-5", "2160-1", "718", "abc-1", "7187"])
def test_typos_and_malformed_codes_are_rejected(code: str) -> None:
    assert not is_valid_loinc(code)


def test_check_digit_matches_the_loinc_users_guide_example() -> None:
    # The LOINC Users' Guide works through the number 12345, whose check digit is 5.
    assert check_digit("12345") == 5
