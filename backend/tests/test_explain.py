"""Explanation pieces without a database: validator rules, template, prompt hygiene, narration text."""

import copy
import json

import pytest

from app.explain.payload import TestItem, allowed_numbers, renderings
from app.explain.prompt import messages, output_schema
from app.explain.template import template_explanation
from app.explain.tts import narration_text
from app.explain.validator import validate
from tests.explain_fixtures import GOOD, GOOD_HI, good, passages, payload, with_text


def codes(content: dict, language: str = "en") -> set[str]:
    return {p.code for p in validate(content, payload(), passages(), language)}


def test_a_faithful_explanation_passes() -> None:
    assert validate(GOOD, payload(), passages(), "en") == []
    assert validate(GOOD_HI, payload(), passages(), "hi") == []


def test_every_number_must_come_from_the_input() -> None:
    assert renderings("1.10") == {"1.1", "1"}
    assert {"53", "1.42", "1.4", "0.72", "13", "17", "15", "97", "40", "49"} <= allowed_numbers(payload())
    assert codes(with_text("means", "Normal is under 1.1.")) == {"number"}
    assert codes(with_text("means", "पहले यह ११.८ था।", GOOD_HI), "hi") == {"number"}  # Devanagari digits too


def test_statuses_coverage_and_order_are_fixed() -> None:
    c = copy.deepcopy(GOOD)
    c["per_test"][1]["status"] = "normal"
    assert codes(c) == {"status"}
    c = copy.deepcopy(GOOD)
    c["per_test"].reverse()
    assert "coverage" in codes(c)
    c = copy.deepcopy(GOOD)
    c["per_test"].pop()
    assert "coverage" in codes(c)


def test_citations_must_be_given_and_belong_to_the_test() -> None:
    c = copy.deepcopy(GOOD)
    c["per_test"][0]["citations"] = []
    assert codes(c) == {"citation"}
    c["per_test"][0]["citations"] = ["P2"]  # a haemoglobin passage cited for creatinine
    assert codes(c) == {"citation"}
    c["per_test"][0]["citations"] = ["P9"]
    assert codes(c) == {"citation"}


def test_structure_language_and_script() -> None:
    assert codes(good(disclaimer_key="none")) == {"disclaimer"}
    assert codes(good(doctor_questions=["Why?"])) == {"questions"}
    assert "language" in codes(good(language="hi"), "en")
    assert codes(dict(GOOD, language="hi"), "hi") == {"script"}  # English text labelled Hindi
    assert codes(good(summary="x" * 2000)) == {"length"}


def test_odia_patterns_and_script() -> None:
    c = good(language="or", summary="ଆପଣଙ୍କ ଦୁଇଟି ଫଳାଫଳ ସୀମା ବାହାରେ ଅଛି। ଚିନ୍ତା କରିବାର କିଛି ନାହିଁ।")
    for t in c["per_test"]:
        t["what_it_measures"] = "ଏହି ପରୀକ୍ଷା ରକ୍ତରେ ଏକ ପଦାର୍ଥ ମାପେ।"
        t["what_this_result_means"] = "ଆପଣଙ୍କ ଡାକ୍ତରଙ୍କ ସହ କଥା ହୁଅନ୍ତୁ।"
    c["doctor_questions"] = ["ଏହାର କାରଣ କ'ଣ?", "ପୁଣି ପରୀକ୍ଷା କରିବା ଉଚିତ କି?"]
    assert codes(c, "or") == {"reassurance"}


@pytest.mark.parametrize("language", ["en", "hi", "or"])
def test_the_template_always_passes_the_validator(language: str) -> None:
    t = template_explanation(payload(), language)
    assert validate(t, payload(), [], language) == []
    assert "1.42" in t["per_test"][0]["what_this_result_means"]


def test_template_for_critical_values_says_contact_a_doctor_today() -> None:
    p = payload()
    p.critical = ["potassium"]
    assert "contact a doctor today" in template_explanation(p, "en")["summary"]


def test_prompt_holds_no_identifiers_and_pins_the_schema() -> None:
    msgs = messages(payload(), passages(), "hi")
    assert "Hindi" in msgs[0]["content"] and "DATA" in msgs[1]["content"]
    assert "Ramesh" not in json.dumps(msgs) and "2026" not in msgs[1]["content"]
    schema = output_schema(["creatinine", "hb"], ["P1", "P2"])
    item = schema["properties"]["per_test"]["items"]
    assert item["properties"]["test_code"]["enum"] == ["creatinine", "hb"]
    assert item["properties"]["citations"]["items"]["enum"] == ["P1", "P2"]
    assert schema["additionalProperties"] is False


def test_narration_reads_summary_results_and_questions() -> None:
    text = narration_text(GOOD, "en")
    assert text.startswith("Your results.") and "Questions for your doctor." in text
    assert text.count("\n") >= 6


def test_symptom_table_is_valid_and_grounded() -> None:
    from pathlib import Path

    from app.catalogue import read_catalogue
    from app.catalogue.symptoms import read_symptoms
    from app.core.config import settings

    data = Path(settings.data_dir) / "catalogue"
    table = read_symptoms(data / "symptoms.csv", {t.code for t in read_catalogue(data).tests})
    assert len(table) >= 70
    assert all(s.source.startswith("https://medlineplus.gov/lab-tests/") for s in table.values())
    assert table[("ldl", "high")].kind == "none" and not table[("ldl", "high")].names["en"]
    assert "tiredness" in table[("hb", "low")].names["en"] and "थकान" in table[("hb", "low")].names["hi"]


@pytest.mark.parametrize("language", ["en", "hi", "or"])
def test_summary_lists_each_out_of_range_result_with_its_range_and_symptoms(language: str) -> None:
    summary = template_explanation(payload(), language)["summary"]
    lines = summary.split("\n")
    bullets = [line for line in lines if line.startswith("• ")]
    assert len(bullets) == 2 and "Creatinine 1.42" in bullets[0].replace(" is ", " ") and "0.72–1.3" in bullets[0]
    assert "Haemoglobin" in bullets[1] and "13–17" in bullets[1]
    words = {"en": "tiredness", "hi": "थकान", "or": "ଥକାପଣ"}[language]
    assert words in bullets[1]


def test_summary_says_when_a_result_usually_has_no_symptoms() -> None:
    p = payload()
    p.focus = [TestItem("ldl", "LDL cholesterol", "heart", 180, "mg/dL", None, 100.0, "lab", "high")]
    p.outside_range = 1
    summary = template_explanation(p, "en")["summary"]
    assert "LDL cholesterol is 180 mg/dL; the lab's range is below 100." in summary
    assert "usually doesn't cause symptoms" in summary and summary.endswith("about these results.")
    assert validate(template_explanation(p, "en"), p, [], "en") == []


def test_narration_drops_the_bullets() -> None:
    text = narration_text(template_explanation(payload(), "en"), "en")
    assert "•" not in text and "Creatinine is 1.42 mg/dL" in text
