"""Map a printed test name to a catalogue test.

Matching uses the catalogue's aliases, compared with spaces and punctuation
removed (OCR often drops spaces). The report section ("LIPID PROFILE") and the
printed unit break ties: "RBC" with "/hpf" in the urine section is the urine
test, "RBC" with "million/cumm" is the blood count. Names that stay ambiguous
are returned with candidates for the user (or an optional local model) to pick.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Protocol

from rapidfuzz import fuzz

from app.catalogue.convert import UnitConverter
from app.catalogue.data import CatalogueData
from app.catalogue.qualitative import is_qualitative

ACCEPT = 0.86  # fuzzy score needed to accept a match without help
MARGIN = 0.04  # best candidate must beat the runner-up (a different test) by this much
_PREFIX = re.compile(r"^(?:serum|plasma|blood|sr|s)(?=[a-z])")  # longest first: "serum" before "s"
_SPECIMEN_SUFFIX = re.compile(r"(?<=[a-z])(?:serum|plasma|wholeblood)$")
_PERCENT_SUFFIX = re.compile(r"(?:percentage|percent)$")

# Words that change which test a name refers to. A match that isn't exact must agree on all of them: "LDL
# cholesterol direct" is not HDL, the trig/HDL ratio is not the TC/HDL ratio, an absolute count is not a
# percentage, and a ratio is not either of its parts. Long words are found inside the squashed name (PDF text
# layers split words: "TRIG LYCERIDES"); short ones only as whole words.
_DISCRIMINATE_LONG = [  # longest first, so "nonhdl" is not also read as "hdl"
    ("highsensitiv", ("hs",)), ("unconjugated", ("indirect",)), ("triglyceride", ("tg",)), ("postprandial", ("pp",)),
    ("conjugated", ("direct",)), ("aspartate", ("ast",)), ("nucleated", ("nrbc",)), ("absolute", ("abs",)),
    ("immature", ("ig",)), ("indirect", ("indirect",)), ("alanine", ("alt",)), ("fasting", ("fast",)),
    ("nonhdl", ("non",)), ("direct", ("direct",)), ("random", ("rand",)),
    ("ratio", ("ratio",)), ("index", ("index",)), ("rdwsd", ("sd",)), ("hscrp", ("hs",)),
    ("vldl", ("vldl",)), ("sgot", ("ast",)), ("sgpt", ("alt",)), ("trig", ("tg",)), ("free", ("free",)),
    ("hdl", ("hdl",)), ("ldl", ("ldl",)),
]
_DISCRIMINATE_SHORT = {"tc": ("tc",), "tg": ("tg",), "ast": ("ast",), "alt": ("alt",), "abs": ("abs",),
                       "pp": ("pp",), "hs": ("hs",), "sd": ("sd",), "t3": ("t3",), "t4": ("t4",),
                       "ft3": ("free", "t3"), "ft4": ("free", "t4"), "non": ("non",)}
# A percentage and the matching absolute count share their plain name; the printed unit tells them apart.
_PAIRS = [("neut_pct", "neut_abs"), ("lymph_pct", "lymph_abs"), ("mono_pct", "mono_abs"), ("eos_pct", "eos_abs"),
          ("baso_pct", "baso_abs"), ("ig_pct", "ig_abs"), ("nrbc_pct", "nrbc_abs")]
UNIT_SIBLINGS = {**dict(_PAIRS), **{b: a for a, b in _PAIRS}}
# "Direct" and "indirect" only tell bilirubins apart; "HDL cholesterol - direct" is still HDL.
_SCOPED = {"direct": "bilirubin", "indirect": "bilirubin"}
# In a ratio, which part comes first matters: LDL/HDL is not HDL/LDL.
_RATIO_PARTS = {"hdl", "ldl", "vldl", "non", "tc", "tg", "ast", "alt"}


def squash(name: str) -> str:
    """Lower-case letters, digits, % and + only: 'S. Creatinine' → 'screatinine'."""
    return re.sub(r"[^a-z0-9%+]", "", name.casefold())


def discriminators(name: str) -> frozenset[str]:
    """The words in a name that decide which test it is (see _DISCRIMINATE_LONG), as tags."""
    text = name.casefold()
    key = squash(name)
    first: dict[str, int] = {}  # tag → where it first appears in the squashed name
    rest = key
    for word, tags in _DISCRIMINATE_LONG:
        at = rest.find(word)
        if at >= 0:
            for tag in tags:
                first[tag] = min(first.get(tag, at), at)
            rest = rest.replace(word, "|" * len(word))
    for m in re.finditer(r"[a-z0-9]+", text):
        for tag in _DISCRIMINATE_SHORT.get(m.group(), ()):
            at = len(squash(text[:m.start()]))
            first[tag] = min(first.get(tag, at), at)
    found = {t for t in first if t not in _SCOPED or _SCOPED[t] in key}
    parts = sorted((first[t], t) for t in found & _RATIO_PARTS)
    if "ratio" in found and len(parts) >= 2:
        found.add("lead:" + parts[0][1])
    return frozenset(found)


def _variants(raw_name: str, inner: bool = True) -> list[str]:
    """Keys to look up, most literal first: the name, without a specimen word, without the bracketed part
    ("Hematocrit (PCV)" → "hematocrit"), then what's in the brackets ("pcv"), with "percentage" read as "%"."""
    base = re.sub(r"\([^)]*\)", " ", raw_name)
    texts = [raw_name, base, *(re.findall(r"\(([^)]*)\)", raw_name) if inner else [])]
    keys: list[str] = []
    for text in texts:
        key = squash(text)
        for k in (key, _PREFIX.sub("", key), _SPECIMEN_SUFFIX.sub("", key), _PERCENT_SUFFIX.sub("%", key)):
            if k and k not in keys:
                keys.append(k)
    return keys


@dataclass(frozen=True)
class Match:
    test_code: str | None
    score: float  # 0–1
    method: str  # exact | fuzzy | resolver | none
    candidates: tuple[tuple[str, float], ...] = ()


class NameResolver(Protocol):
    """Picks one of the candidate tests for an ambiguous name, or None (e.g. a small local LLM)."""

    def resolve(self, raw_name: str, section: str | None, raw_unit: str | None,
                candidates: list[tuple[str, str]]) -> str | None: ...


class CatalogueMatcher:
    def __init__(self, catalogue: CatalogueData, converter: UnitConverter, resolver: NameResolver | None = None):
        self.converter = converter
        self.resolver = resolver
        self.panel = {t.code: t.panel for t in catalogue.tests}
        self.names = {t.code: t.name for t in catalogue.tests}
        self.index: dict[str, set[str]] = defaultdict(set)
        self.tags: dict[str, frozenset[str]] = {}
        for t in catalogue.tests:
            for alias in (t.name, t.short, *t.aliases):
                key = squash(alias)
                if key:
                    self.index[key].add(t.code)
                    self.tags.setdefault(key, discriminators(alias))
        self.keys = list(self.index)

    def _context(self, code: str, section: str | None, unit: str | None) -> float:
        """Bonus (or penalty) from the section and unit printed next to the name."""
        bonus = 0.0
        if section and self.panel[code] == section:
            bonus += 0.05
        if unit:
            bonus += 0.05 if self.converter.supports(code, unit) else -0.2
        return bonus

    def match(self, raw_name: str, section: str | None = None, raw_unit: str | None = None,
              in_words: bool | None = None) -> Match:
        """`in_words`: whether the result is a word ("Absent") rather than a number; None when unknown. A word
        answer only matches a test reported in words, and a number only one reported in numbers."""
        found = self._match(raw_name, section, raw_unit, in_words)
        return self._unit_sibling(found, raw_name, raw_unit)

    def _unit_sibling(self, found: Match, raw_name: str, raw_unit: str | None) -> Match:
        """"Neutrophils 3.74 x10³/µL" in an absolute-count block is the count, not the percentage. A name that
        says which one it is ("absolute", "%") is believed over the unit; the review shows the unit doesn't fit."""
        code = found.test_code
        sibling = UNIT_SIBLINGS.get(code) if code else None
        explicit = "abs" in discriminators(raw_name) or re.search(r"%|percent", raw_name, re.I)
        if (sibling and raw_unit and not explicit and sibling in self.panel
                and not self.converter.supports(code, raw_unit) and self.converter.supports(sibling, raw_unit)):
            return Match(sibling, found.score, found.method, found.candidates)
        return found

    def _match(self, raw_name: str, section: str | None, raw_unit: str | None, in_words: bool | None) -> Match:
        key = squash(raw_name)
        if not key:
            return Match(None, 0.0, "none")

        def kind_ok(code: str) -> bool:
            return is_qualitative(code) == bool(in_words)  # unknown counts as a number

        tags = discriminators(raw_name)
        for i, k in enumerate(_variants(raw_name)):
            exact = {c for c in self.index.get(k, ()) if kind_ok(c)}
            if exact and (i == 0 or self.tags[k] == tags):  # the name as printed is trusted as it stands
                ranked = sorted(exact, key=lambda c: self._context(c, section, raw_unit), reverse=True)
                scores = [(c, min(1.0, 0.95 + self._context(c, section, raw_unit))) for c in ranked]
                if len(ranked) == 1 or scores[0][1] - scores[1][1] >= MARGIN:
                    return Match(ranked[0], scores[0][1], "exact", tuple(scores[:3]))
                return self._ambiguous(raw_name, section, raw_unit, scores)

        variants = _variants(raw_name, inner=False)  # a bracketed abbreviation alone is too short to compare
        best: dict[str, float] = {}
        for alias_key in self.keys:
            if self.tags[alias_key] != tags:
                continue
            s = max(fuzz.ratio(v, alias_key) for v in variants) / 100
            if s < 0.6:
                continue
            for code in self.index[alias_key]:
                if kind_ok(code):
                    best[code] = max(best.get(code, 0.0), s)
        if not best:
            return Match(None, 0.0, "none")
        scores = sorted(((c, min(1.0, s + self._context(c, section, raw_unit))) for c, s in best.items()),
                        key=lambda cs: cs[1], reverse=True)
        top, top_score = scores[0]
        runner = scores[1][1] if len(scores) > 1 else 0.0
        if top_score >= ACCEPT and top_score - runner >= MARGIN:
            return Match(top, top_score, "fuzzy", tuple(scores[:3]))
        return self._ambiguous(raw_name, section, raw_unit, scores)

    def _ambiguous(self, raw_name: str, section: str | None, raw_unit: str | None,
                   scores: list[tuple[str, float]]) -> Match:
        candidates = tuple(scores[:3])
        if self.resolver is not None:
            picked = self.resolver.resolve(raw_name, section, raw_unit,
                                           [(c, self.names[c]) for c, _ in candidates])
            if picked in {c for c, _ in candidates}:
                return Match(picked, 0.75, "resolver", candidates)
        return Match(None, candidates[0][1] if candidates else 0.0, "none", candidates)
