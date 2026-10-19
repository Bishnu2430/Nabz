"""Results reported in words: urine dipstick and microscopy findings ("Absent", "Trace", "++", "Pale yellow").

Each answer is stored with a score so the rest of the pipeline can treat it like any other result: the usual answer
scores 0, and anything else scores above it, so the catalogue's range (upper limit 0) marks it as outside the usual
answer. What people see is always the answer itself (`Answer.code`, translated in the app), never the score.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Answer:
    code: str  # stable key, translated in the app ("absent", "plus2", "pale_yellow")
    score: Decimal  # 0 is the usual answer


# answer code → score, and the spellings that read as it
_PRESENCE = {
    "absent": (0, ("absent", "negative", "nil", "neg", "not detected", "none", "none seen", "not seen",
                   "not present", "-ve", "non reactive")),
    "trace": (Decimal("0.5"), ("trace", "traces", "occasional", "rare", "few")),
    "present": (1, ("present", "positive", "detected", "+ve", "seen", "reactive")),
    "plus1": (1, ("+", "1+", "+1", "(+)")),
    "plus2": (2, ("++", "2+", "+2", "(++)", "moderate")),
    "plus3": (3, ("+++", "3+", "+3", "(+++)", "many", "plenty", "numerous")),
    "plus4": (4, ("++++", "4+", "+4", "(++++)")),
}
_UROBILINOGEN = {
    "normal": (0, ("normal", "normal (0.2)", "absent", "negative", "nil", "trace", "not increased")),
    "increased": (1, ("increased", "present", "positive", "+", "1+", "high")),
    "plus2": (2, ("++", "2+")),
    "plus3": (3, ("+++", "3+")),
}
_COLOUR = {
    "colourless": (0, ("colourless", "colorless", "clear")),
    "pale_yellow": (0, ("pale yellow", "light yellow", "straw", "straw yellow", "pale straw")),
    "yellow": (0, ("yellow",)),
    "dark_yellow": (1, ("dark yellow", "deep yellow")),
    "amber": (1, ("amber", "orange", "orange yellow")),
    "red": (2, ("red", "reddish", "pink", "blood stained", "bloody")),
    "brown": (2, ("brown", "dark brown", "cola", "tea coloured", "tea colored")),
    "other": (2, ("green", "blue", "milky", "white", "greenish")),
}
_CLARITY = {
    "clear": (0, ("clear", "transparent")),
    "slightly_turbid": (1, ("slightly turbid", "slightly cloudy", "slightly hazy", "hazy", "faintly turbid")),
    "turbid": (2, ("turbid", "cloudy", "very turbid", "opaque")),
}

SCALES = {"presence": _PRESENCE, "urobilinogen": _UROBILINOGEN, "colour": _COLOUR, "clarity": _CLARITY}

# Which tests are read in words, and on which scale.
QUALITATIVE: dict[str, str] = {
    "urine_colour": "colour", "urine_appearance": "clarity", "urine_urobilinogen": "urobilinogen",
    **{code: "presence" for code in (
        "urine_protein", "urine_glucose", "urine_ketones", "urine_bilirubin", "urine_blood", "urine_nitrite",
        "urine_le", "urine_bile_salts", "urine_mucus", "urine_casts", "urine_crystals", "urine_bacteria",
        "urine_yeast", "urine_parasites")},
}

_LOOKUP: dict[str, dict[str, Answer]] = {
    name: {spelling: Answer(code, Decimal(score)) for code, (score, spellings) in scale.items()
           for spelling in spellings}
    for name, scale in SCALES.items()
}
WORDS: frozenset[str] = frozenset(s for table in _LOOKUP.values() for s in table)
USUAL: dict[str, str] = {"presence": "absent", "urobilinogen": "normal", "colour": "pale_yellow", "clarity": "clear"}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().casefold()).strip(" .:")


def is_answer(text: str) -> bool:
    """Whether the printed text is a word answer on any scale (used by the parser, which knows no tests)."""
    return _clean(text) in WORDS


def is_qualitative(test_code: str | None) -> bool:
    return test_code in QUALITATIVE


def read_answer(test_code: str, text: str | None) -> Answer | None:
    """The answer printed for a test reported in words, or None if it isn't one we know."""
    scale = QUALITATIVE.get(test_code)
    if scale is None or not text:
        return None
    return _LOOKUP[scale].get(_clean(text))


def answer_code(test_code: str | None, text: str | None) -> str | None:
    """The answer's code for a test reported in words ("absent"), or None for a test reported in numbers."""
    answer = read_answer(test_code, text) if test_code else None
    return answer.code if answer else None


def usual_answer(test_code: str) -> str | None:
    scale = QUALITATIVE.get(test_code)
    return USUAL[scale] if scale else None
