"""Results reported in words: reading the answer, and saying it back without a number."""

from decimal import Decimal

import pytest

from app.catalogue.qualitative import answer_code, is_answer, read_answer, usual_answer
from app.explain.payload import Payload, TestItem
from app.explain.template import template_explanation


@pytest.mark.parametrize(
    ("code", "text", "answer", "score"),
    [
        ("urine_protein", "ABSENT", "absent", 0), ("urine_protein", "Nil", "absent", 0),
        ("urine_protein", "Negative", "absent", 0), ("urine_glucose", "Trace", "trace", Decimal("0.5")),
        ("urine_glucose", "++", "plus2", 2), ("urine_ketones", "3+", "plus3", 3),
        ("urine_blood", "Positive", "present", 1), ("urine_colour", "Pale Yellow", "pale_yellow", 0),
        ("urine_colour", "straw", "pale_yellow", 0), ("urine_colour", "Red", "red", 2),
        ("urine_appearance", "CLEAR", "clear", 0), ("urine_appearance", "Slightly turbid", "slightly_turbid", 1),
        ("urine_urobilinogen", "Normal", "normal", 0),
    ],
)
def test_reads_the_answer(code: str, text: str, answer: str, score) -> None:
    found = read_answer(code, text)
    assert found is not None and (found.code, found.score) == (answer, Decimal(score))
    assert answer_code(code, text) == answer


def test_numbers_and_unknown_words_are_not_answers() -> None:
    assert read_answer("urine_protein", "30") is None
    assert read_answer("urine_protein", "smells sweet") is None
    assert read_answer("hb", "Absent") is None  # haemoglobin is reported in numbers
    assert answer_code("hb", "13.2") is None
    assert is_answer("ABSENT") and is_answer("Pale yellow") and not is_answer("Ready")
    assert usual_answer("urine_colour") == "pale_yellow" and usual_answer("hb") is None


def _item(answer: str, status: str) -> TestItem:
    return TestItem(test_code="urine_protein", test="Urine protein", organ="urinary", value=None, unit=None,
                    range_low=None, range_high=None, range_source="typical", status=status, answer=answer,
                    usual="absent")


def test_the_explanation_says_the_answer_in_words() -> None:
    payload = Payload(age_band="30–39", sex="female", results_total=1, outside_range=1,
                      focus=[_item("plus2", "high")])
    en = template_explanation(payload, "en")
    line = en["per_test"][0]["what_this_result_means"]
    assert line == "Urine protein is present (++); usually it is absent."
    assert "Urine protein is present (++)" in en["summary"]
    hi = template_explanation(payload, "hi")["per_test"][0]["what_this_result_means"]
    assert "मिला (++)" in hi and "नहीं मिला" in hi
    usual = template_explanation(Payload(age_band=None, sex="male", results_total=1, outside_range=0,
                                         focus=[_item("absent", "normal")]), "en")
    assert usual["per_test"][0]["what_this_result_means"] == "Urine protein is absent, as is usual."
