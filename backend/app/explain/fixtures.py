"""A fixed de-identified payload, its passages and a generated explanation that passes every check.

The red-team suites add unsafe text to this explanation and expect the checks to catch it: in the tests, and on
demand from the safety console. Nothing here comes from a real person.
"""

from __future__ import annotations

import copy

from app.explain.payload import Payload, TestItem
from app.explain.prompt import DISCLAIMER_KEY, Passage


def payload() -> Payload:
    return Payload(
        age_band="40–49", sex="male", results_total=53, outside_range=2,
        focus=[
            TestItem("creatinine", "Creatinine", "kidney", 1.42, "mg/dL", 0.72, 1.3, "lab", "high",
                     change={"percent": 15, "direction": "up", "significant": True, "previous_value": 1.24,
                             "months_since_previous": 12},
                     trend={"direction": "rising", "confirmed": True, "results": 5, "years": 4},
                     percentile={"value": 97, "side": "above", "population": "US men aged 40–49"}),
            TestItem("hb", "Haemoglobin", "blood", 12.1, "g/dL", 13.0, 17.0, "lab", "low"),
        ],
        others=["Platelet count", "Sodium"],
    )


def passages() -> list[Passage]:
    return [
        Passage("P1", "00000000-0000-0000-0000-000000000001", "creatinine", "Creatinine Test",
                "What do the results mean?\nHigh levels of creatinine in the blood may mean the kidneys are not "
                "working well."),
        Passage("P2", "00000000-0000-0000-0000-000000000002", "hb", "Hemoglobin Test",
                "What do the results mean?\nLower than normal hemoglobin levels may be a sign of anemia."),
    ]


GOOD = {
    "language": "en",
    "summary": "Two of your 53 results are outside the lab's range: creatinine is high and haemoglobin is low. "
               "The rest are within range. Please talk to your doctor about these two results.",
    "per_test": [
        {"test_code": "creatinine", "status": "high",
         "what_it_measures": "Creatinine is a waste product that your kidneys filter out of the blood.",
         "what_this_result_means": "Your creatinine is 1.42 mg/dL, above the lab's range of 0.72 to 1.3. It is 15% "
                                   "higher than 12 months ago and has been rising for 4 years. A high result can be "
                                   "linked with how well the kidneys are working.",
         "citations": ["P1"]},
        {"test_code": "hb", "status": "low",
         "what_it_measures": "Haemoglobin is the protein in red blood cells that carries oxygen.",
         "what_this_result_means": "Your haemoglobin is 12.1 g/dL, below the lab's range of 13 to 17. A low result "
                                   "can be linked with anaemia, which your doctor can look into.",
         "citations": ["P2"]},
    ],
    "doctor_questions": ["What could explain my high creatinine?", "Should my kidney tests be repeated, and when?",
                         "What could explain my low haemoglobin?"],
    "disclaimer_key": DISCLAIMER_KEY,
}


GOOD_HI = {
    "language": "hi",
    "summary": "आपके 53 में से दो परिणाम लैब की सीमा से बाहर हैं: क्रिएटिनिन अधिक है और हीमोग्लोबिन कम है। बाकी परिणाम सीमा "
               "के भीतर हैं। इन दो परिणामों के बारे में अपने डॉक्टर से बात करें।",
    "per_test": [
        {"test_code": "creatinine", "status": "high",
         "what_it_measures": "क्रिएटिनिन एक अपशिष्ट पदार्थ है जिसे गुर्दे खून से छानते हैं।",
         "what_this_result_means": "आपका क्रिएटिनिन 1.42 mg/dL है, जो लैब की सीमा 0.72 से 1.3 से अधिक है। यह 12 महीने "
                                   "पहले से 15% अधिक है और 4 वर्षों से बढ़ रहा है।",
         "citations": ["P1"]},
        {"test_code": "hb", "status": "low",
         "what_it_measures": "हीमोग्लोबिन लाल रक्त कोशिकाओं का वह प्रोटीन है जो ऑक्सीजन ले जाता है।",
         "what_this_result_means": "आपका हीमोग्लोबिन 12.1 g/dL है, जो लैब की सीमा 13 से 17 से कम है। आपके डॉक्टर इसकी "
                                   "जाँच कर सकते हैं।",
         "citations": ["P2"]},
    ],
    "doctor_questions": ["मेरे क्रिएटिनिन के अधिक होने का क्या कारण हो सकता है?", "क्या गुर्दे की जाँच दोबारा करानी चाहिए?",
                         "मेरे हीमोग्लोबिन के कम होने का क्या कारण हो सकता है?"],
    "disclaimer_key": DISCLAIMER_KEY,
}


def good(**changes) -> dict:
    """A copy of GOOD with top-level fields replaced."""
    c = copy.deepcopy(GOOD)
    c.update(changes)
    return c


def with_text(field: str, text: str, base: dict | None = None) -> dict:
    """GOOD (or `base`) with `text` appended to one field: summary, measures, means (first test) or question."""
    c = copy.deepcopy(base or GOOD)
    if field == "summary":
        c["summary"] += " " + text
    elif field == "measures":
        c["per_test"][0]["what_it_measures"] += " " + text
    elif field == "means":
        c["per_test"][0]["what_this_result_means"] += " " + text
    else:
        c["doctor_questions"].append(text)
    return c
