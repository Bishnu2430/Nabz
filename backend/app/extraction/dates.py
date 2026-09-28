"""Find the sample collection date in a report header.

Trends need each result's date. Reports print several: registered, collected, received and reported, usually
hours apart. The collection date is the clinically right one, so labels are ranked and the best-ranked label
with a readable date wins. Indian reports write dates day-first (30/06/2024, 30-Jun-2024).
"""

from __future__ import annotations

import re
from datetime import date

# Higher wins. "Reported" is a fallback: usually the same day or the next.
LABELS = (
    (3, re.compile(r"(?:sample\s*)?(?:collect(?:ed|ion)|drawn)", re.I)),
    (2, re.compile(r"sample\s*date|received|receiving", re.I)),
    (1, re.compile(r"regist(?:ered|ration)|booked|booking", re.I)),
    (0, re.compile(r"report(?:ed|ing)?(?:\s*(?:on|date))?|date", re.I)),
)

MONTHS = {m: i for i, m in enumerate(
    ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), start=1)}

_NUMERIC = re.compile(r"(?<!\d)(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{4}|\d{2})(?!\d)")
_ISO = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")
_NAMED = re.compile(r"(?<!\d)(\d{1,2})(?:st|nd|rd|th)?[\s\-/]*([A-Za-z]{3,9})[\s\-/,]*(\d{4}|\d{2})(?!\d)")


def _year(text: str) -> int:
    y = int(text)
    return y + 2000 if y < 100 else y


def _make(y: int, m: int, d: int, today: date) -> date | None:
    try:
        found = date(y, m, d)
    except ValueError:
        return None
    return found if date(2000, 1, 1) <= found <= today else None


def parse_date(text: str, today: date | None = None) -> tuple[int, date] | None:
    """(position, date) of the first date in `text`, day-first."""
    today = today or date.today()
    candidates: list[tuple[int, date]] = []
    for m in _ISO.finditer(text):
        if d := _make(int(m[1]), int(m[2]), int(m[3]), today):
            candidates.append((m.start(), d))
    for m in _NUMERIC.finditer(text):
        if d := _make(_year(m[3]), int(m[2]), int(m[1]), today):
            candidates.append((m.start(), d))
    for m in _NAMED.finditer(text):
        month = MONTHS.get(m[2][:3].lower())
        if month and (d := _make(_year(m[3]), month, int(m[1]), today)):
            candidates.append((m.start(), d))
    return min(candidates, key=lambda c: c[0]) if candidates else None


def find_collection_date(lines: list[str], today: date | None = None) -> date | None:
    """The date after the best-ranked label on any line (a header line may hold two label/value pairs)."""
    best: tuple[int, date] | None = None
    for text in lines:
        for rank, pattern in LABELS:
            if best is not None and rank <= best[0]:
                break
            for label in pattern.finditer(text):
                found = parse_date(text[label.end():], today)
                if found is not None:
                    best = (rank, found[1])
                    break
    return best[1] if best else None
