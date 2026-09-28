"""Collection-date reading from report headers."""

from datetime import date

import pytest

from app.extraction.dates import find_collection_date, parse_date

TODAY = date(2026, 9, 28)


@pytest.mark.parametrize(("text", "expected"), [
    ("30/06/2024 08:15", date(2024, 6, 30)),
    ("30-06-2024", date(2024, 6, 30)),
    ("30.06.24", date(2024, 6, 30)),
    ("30-Jun-2024 8:15 AM", date(2024, 6, 30)),
    ("30 June 2024", date(2024, 6, 30)),
    ("1st Mar 2025", date(2025, 3, 1)),
    ("2024-06-30T08:15", date(2024, 6, 30)),
    ("05/06/2024", date(2024, 6, 5)),  # day first, as Indian reports print it
])
def test_parse_date(text: str, expected: date) -> None:
    assert parse_date(text, TODAY)[1] == expected


@pytest.mark.parametrize("text", ["31/02/2024", "12/12/2031", "Lab No. 84127575", "13/2024", "Age 45 Y"])
def test_parse_date_rejects(text: str) -> None:
    assert parse_date(text, TODAY) is None


def test_collection_beats_other_dates_on_the_same_line() -> None:
    lines = [
        "Anvaya Diagnostics",
        "Patient Name: A. Kumar      Registered: 01/07/2024 07:50",
        "Age / Sex: 45 Y / Male      Reported: 02/07/2024 17:40",
        "Ref. By: Dr. S. Rao         Sample Collected On: 01/07/2024 08:15",
    ]
    assert find_collection_date(lines, TODAY) == date(2024, 7, 1)
    lines[3] = "Ref. By: Dr. S. Rao"
    assert find_collection_date(lines, TODAY) == date(2024, 7, 1)  # registered outranks reported


def test_ocr_spacing_and_missing_dates() -> None:
    assert find_collection_date(["Collected:30/06/2024"], TODAY) == date(2024, 6, 30)
    assert find_collection_date(["Collection Date : 30 - 06 - 2024"], TODAY) == date(2024, 6, 30)
    assert find_collection_date(["Haemoglobin 14.2 g/dL 13.0 - 17.0"], TODAY) is None
