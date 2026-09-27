"""Group positioned tokens into visual lines and horizontal segments."""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from app.extraction.types import Token


@dataclass
class Segment:
    text: str
    x0: float
    x1: float
    tokens: list[Token]


@dataclass
class Line:
    tokens: list[Token]
    segments: list[Segment]

    @property
    def top(self) -> float:
        return min(t.top for t in self.tokens)

    @property
    def bottom(self) -> float:
        return max(t.bottom for t in self.tokens)

    @property
    def text(self) -> str:
        return " ".join(s.text for s in self.segments)


def group_lines(tokens: list[Token]) -> list[Line]:
    """Cluster tokens whose vertical centres are close, then split each line into segments."""
    if not tokens:
        return []
    median_h = statistics.median(t.height for t in tokens) or 1.0
    ordered = sorted(tokens, key=lambda t: (t.cy, t.x0))
    rows: list[list[Token]] = []
    centres: list[float] = []
    for tok in ordered:
        if rows and abs(tok.cy - centres[-1]) <= 0.45 * median_h:
            rows[-1].append(tok)
            centres[-1] = statistics.fmean(t.cy for t in rows[-1])
        else:
            rows.append([tok])
            centres.append(tok.cy)
    return [Line(sorted(r, key=lambda t: t.x0), _segments(sorted(r, key=lambda t: t.x0), median_h)) for r in rows]


def _segments(tokens: list[Token], median_h: float) -> list[Segment]:
    """Merge tokens separated by less than about one character width."""
    gap_limit = 0.55 * median_h
    segments: list[Segment] = []
    for tok in tokens:
        if segments and tok.x0 - segments[-1].x1 <= gap_limit:
            last = segments[-1]
            sep = "" if tok.x0 - last.x1 < 0.12 * median_h else " "
            segments[-1] = Segment(last.text + sep + tok.text, last.x0, max(last.x1, tok.x1), [*last.tokens, tok])
        else:
            segments.append(Segment(tok.text, tok.x0, tok.x1, [tok]))
    return segments
