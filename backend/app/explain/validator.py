"""Deterministic checks on a generated explanation (FR-24, ADR-0005, hazards S-03 – S-06, S-08).

`validate()` returns a list of problems; an empty list means the explanation may go on to the LLM judge. Any
problem sends the report to the template instead. The rules err on the side of rejecting: a good explanation
lost to the template costs less than a bad one shown.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.explain.payload import Payload, allowed_numbers, normalise
from app.explain.prompt import DISCLAIMER_KEY, Passage

_DIGITS = str.maketrans("०१२३४५६७८९୦୧୨୩୪୫୬୭୮୯", "01234567890123456789")
_NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?")

MAX_SUMMARY = 1800  # a line per out-of-range test, with its symptoms
MAX_FIELD = 700
MAX_QUESTION = 220


@dataclass(frozen=True)
class Problem:
    code: str
    detail: str


_EN = {
    "diagnosis": [
        r"(?<!\bif )(?<!\bwhen )\byou (?:have|may have|might have|probably have|likely have|could have) "
        r"(?!(?:a |an |the |your |some |any |\d+ )?"
        r"(?:results?|tests?|reports?|values?|questions?|range|doctor|appointment|symptoms?|of these|these)\b"
        r"|\d|been\b|to\b|not\b|more\b|less\b|confirmed\b|checked\b|shared\b|uploaded\b|given\b|entered\b|done\b)\w+",
        r"\byou are (?:a )?(?:diabetic|pre-?diabetic|anaemic|anemic|hypothyroid|hyperthyroid|obese|ill|sick)\b",
        r"\b(?:this|these|it) (?:confirms?|proves?|shows? that you have|means you have)\b",
        r"\bsuffering from\b",
        r"\b(?:this|these|it|that|which) (?:results? |values? |levels? )?(?:can |may |might |could |would )?"
        r"(?:suggests?|indicates?|points? to)\b",
        r"\b(?:seen|found|common|happens?) in (?:people with )?(?:\w+ )?(?:disease|disorder|syndrome|cancer|failure)\b",
        r"\b(?:suggesting|indicating)\b",
        r"\b(?:this|these|it|that|which) (?:is|are|may be|might be|could be|can be) (?:a |an )?(?:early )?signs? of\b",
    ],
    "treatment": [
        r"\b\d+(?:\.\d+)?\s?(?:mg|mcg|µg|iu|units?)\b(?!\s*/)",
        r"\b(?:take|start|stop|increase|decrease|reduce|continue) (?:taking )?(?:your |a |an |some )?"
        r"(?:medicines?|medications?|drugs?|tablets?|pills?|insulin|supplements?|iron|vitamins?|dose)\b",
        r"\bprescri(?:be|bed|ption)\b",
        r"\bdos(?:e|es|age)\b",
        r"\b(?:metformin|insulin|statins?|atorvastatin|levothyroxine|thyroxine|aspirin|antibiotics?)\b",
        r"\b(?:avoid|cut down on|eat more|eat less|stop eating|drink more)\b",
    ],
    "reassurance": [
        r"\bnothing to (?:worry|be worried) about\b",
        r"\bno (?:need|reason) to (?:worry|see|consult|visit)\b",
        r"\byou are (?:perfectly |completely )?(?:healthy|fine)\b",
        r"\b(?:don'?t|do not) worry\b",
        r"\b(?:perfectly normal|harmless|not serious|nothing serious)\b",
    ],
    "instruction": [
        r"\bignore (?:all |the |any )?(?:previous|above|earlier|prior)\b",
        r"\b(?:as an ai|language model|system prompt)\b",
        r"https?://|www\.",
    ],
}

_HI = {
    "diagnosis": [r"आपको\s+(?:मधुमेह|डायबिटीज़?|शुगर की बीमारी|एनीमिया|खून की कमी है|किडनी की बीमारी"
                  r"|लिवर की बीमारी|कैंसर|थायरॉइड की बीमारी)",
                  r"आप\s+(?:मधुमेह|डायबिटीज़?)\s+(?:के मरीज़?|से पीड़ित)"],
    "treatment": [r"दवा(?:ई|एँ|ओं)?\s+(?:लें|लीजिए|शुरू|बंद|बढ़ा|घटा)", r"गोली", r"खुराक", r"इंसुलिन", r"मेटफॉर्मिन",
                  r"सप्लीमेंट\s+(?:लें|लीजिए)"],
    "reassurance": [r"चिंता\s+(?:की|करने की)\s+(?:कोई\s+)?(?:बात|ज़रूरत|जरूरत)\s+नहीं", r"आप\s+(?:पूरी तरह\s+)?स्वस्थ\s+हैं",
                    r"घबराने\s+की\s+(?:कोई\s+)?(?:बात|ज़रूरत|जरूरत)\s+नहीं"],
}

# Odia patterns are drafts, pending the native-speaker review (T2.5).
_OR = {
    "diagnosis": [r"ଆପଣଙ୍କର?\s+(?:ମଧୁମେହ|ଡାଇବେଟିସ୍|ରକ୍ତହୀନତା|କର୍କଟ)"],
    "treatment": [r"ଔଷଧ\s+(?:ନିଅନ୍ତୁ|ଖାଆନ୍ତୁ|ବନ୍ଦ)", r"ଡୋଜ୍", r"ଇନସୁଲିନ୍", r"ଟାବଲେଟ୍"],
    "reassurance": [r"ଚିନ୍ତା\s+କରିବାର\s+(?:କିଛି\s+)?(?:ନାହିଁ|ଦରକାର ନାହିଁ)", r"ଆପଣ\s+ସୁସ୍ଥ\s+ଅଛନ୍ତି"],
}

def _nfd(text: str) -> str:
    """Canonical decomposition, so "ज़" typed as one code point or as ज + nukta matches the same pattern."""
    return unicodedata.normalize("NFD", text)


PATTERNS = {
    lang: {kind: [re.compile(_nfd(p), re.IGNORECASE) for p in pats] for kind, pats in table.items()}
    for lang, table in (("en", _EN), ("hi", _HI), ("or", _OR))
}

_SCRIPTS = {"hi": (0x0900, 0x097F), "or": (0x0B00, 0x0B7F)}


def texts(content: dict) -> list[str]:
    out = [str(content.get("summary", ""))]
    for t in content.get("per_test") or []:
        if isinstance(t, dict):
            out += [str(t.get("what_it_measures", "")), str(t.get("what_this_result_means", ""))]
    out += [str(q) for q in content.get("doctor_questions") or []]
    return out


def _allowed_letter(c: str, lang: str) -> bool:
    """Latin (test names and units) is always allowed; µ too; plus the output language's own script."""
    code = ord(c)
    if code < 0x0250 or 0x1E00 <= code <= 0x1EFF or c in "µμ":
        return True
    if lang in _SCRIPTS:
        lo, hi = _SCRIPTS[lang]
        return lo <= code <= hi
    return False


def _script_share(text: str, lang: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 1.0
    if lang == "en":
        return sum(c.isascii() for c in letters) / len(letters)
    lo, hi = _SCRIPTS[lang]
    return sum(lo <= ord(c) <= hi for c in letters) / len(letters)


def validate(content: dict, payload: Payload, passages: list[Passage], language: str) -> list[Problem]:
    problems: list[Problem] = []

    def add(code: str, detail: str) -> None:
        problems.append(Problem(code, detail))

    # Structure
    if content.get("language") != language:
        add("language", f"language is {content.get('language')!r}, expected {language!r}")
    if content.get("disclaimer_key") != DISCLAIMER_KEY:
        add("disclaimer", "disclaimer key missing or wrong")
    entries = [t for t in content.get("per_test") or [] if isinstance(t, dict)]
    if len(entries) != len(content.get("per_test") or []):
        add("structure", "per_test holds something other than objects")
    questions = content.get("doctor_questions") or []
    if not 2 <= len(questions) <= 6:
        add("questions", f"{len(questions)} doctor questions; 2–6 expected")

    # Coverage and statuses: every focus test, in order, with the computed status
    expected = [(t.test_code, t.status) for t in payload.focus]
    got = [(t.get("test_code"), t.get("status")) for t in entries]
    if [c for c, _ in got] != [c for c, _ in expected]:
        add("coverage", f"tests {[c for c, _ in got]} != focus {[c for c, _ in expected]}")
    for (code, status), (_, want) in zip(got, expected, strict=False):
        if status != want:
            add("status", f"{code}: status {status!r}, computed {want!r}")

    # Citations: at least one per test that has passages, and only passages given for that test
    by_label = {p.label: p for p in passages}
    grounded = {p.test_code for p in passages}
    for t in entries:
        cites = t.get("citations") or []
        if not cites and t.get("test_code") in grounded:
            add("citation", f"{t.get('test_code')}: no citation")
        for label in cites:
            p = by_label.get(label)
            if p is None:
                add("citation", f"{t.get('test_code')}: unknown passage {label!r}")
            elif p.test_code != t.get("test_code"):
                add("citation", f"{t.get('test_code')}: cites {label}, a passage about {p.test_code}")

    # Length
    if len(str(content.get("summary", ""))) > MAX_SUMMARY:
        add("length", "summary too long")
    for t in entries:
        if max(len(str(t.get("what_it_measures", ""))), len(str(t.get("what_this_result_means", "")))) > MAX_FIELD:
            add("length", f"{t.get('test_code')}: text too long")
    if any(len(str(q)) > MAX_QUESTION for q in questions):
        add("length", "a doctor question is too long")

    all_text = _nfd("\n".join(texts(content)))

    # Numbers: every number must come from the input (hazard S-04)
    allowed = allowed_numbers(payload)
    for token in _NUMBER.findall(all_text.translate(_DIGITS)):
        if normalise(token) not in allowed:
            add("number", f"{token} is not in the input")

    # Script: the requested language, not English with a few words, and no letters from any other script
    share = _script_share(all_text, language)
    if share < (0.9 if language == "en" else 0.6):
        add("script", f"only {share:.0%} of letters are in the {language} script")
    if stray := sorted({c for c in all_text if c.isalpha() and not _allowed_letter(c, language)}):
        add("script", f"letters from another script: {''.join(stray[:10])}")

    # Passage labels belong in citations, not in the text ("according to P1")
    if m := re.search(r"\bP\d{1,2}\b", all_text):
        add("label", f"passage label {m.group(0)!r} in the text")

    # Banned intents, in the output language and in English (models mix languages)
    for lang in {language, "en"}:
        for kind, patterns in PATTERNS[lang].items():
            for pattern in patterns:
                if m := pattern.search(all_text):
                    add(kind, f"{m.group(0)!r}")
    return problems
