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

ACCEPT = 0.86  # fuzzy score needed to accept a match without help
MARGIN = 0.04  # best candidate must beat the runner-up (a different test) by this much
_PREFIX = re.compile(r"^(?:s|sr|serum|plasma|blood)(?=[a-z])")


def squash(name: str) -> str:
    """Lower-case letters, digits, % and + only: 'S. Creatinine' → 'screatinine'."""
    return re.sub(r"[^a-z0-9%+]", "", name.casefold())


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
        for t in catalogue.tests:
            for alias in (t.name, t.short, *t.aliases):
                key = squash(alias)
                if key:
                    self.index[key].add(t.code)
        self.keys = list(self.index)

    def _context(self, code: str, section: str | None, unit: str | None) -> float:
        """Bonus (or penalty) from the section and unit printed next to the name."""
        bonus = 0.0
        if section and self.panel[code] == section:
            bonus += 0.05
        if unit:
            bonus += 0.05 if self.converter.supports(code, unit) else -0.2
        return bonus

    def match(self, raw_name: str, section: str | None = None, raw_unit: str | None = None) -> Match:
        key = squash(raw_name)
        if not key:
            return Match(None, 0.0, "none")
        for k in (key, _PREFIX.sub("", key)):
            exact = self.index.get(k)
            if exact:
                ranked = sorted(exact, key=lambda c: self._context(c, section, raw_unit), reverse=True)
                scores = [(c, min(1.0, 0.95 + self._context(c, section, raw_unit))) for c in ranked]
                if len(ranked) == 1 or scores[0][1] - scores[1][1] >= MARGIN:
                    return Match(ranked[0], scores[0][1], "exact", tuple(scores[:3]))
                return self._ambiguous(raw_name, section, raw_unit, scores)

        best: dict[str, float] = {}
        for alias_key in self.keys:
            s = max(fuzz.ratio(key, alias_key), fuzz.ratio(_PREFIX.sub("", key), alias_key)) / 100
            if s < 0.6:
                continue
            for code in self.index[alias_key]:
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
