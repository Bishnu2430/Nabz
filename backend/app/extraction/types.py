from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class Token:
    """A run of text with its box in PDF points (top-left origin) on one page."""

    text: str
    x0: float
    top: float
    x1: float
    bottom: float
    conf: float = 1.0

    @property
    def height(self) -> float:
        return self.bottom - self.top

    @property
    def cy(self) -> float:
        return (self.top + self.bottom) / 2


@dataclass
class Page:
    number: int  # 0-based
    width: float  # points
    height: float
    source: str  # "text-layer" or "ocr"
    tokens: list[Token] = field(default_factory=list)
    quality: float | None = None  # 0–1 image quality score (OCR pages only)
    skew: float = 0.0  # degrees the image was rotated before OCR; token boxes are in the rotated frame


@dataclass
class ParsedRow:
    raw_name: str
    raw_value: str
    value: Decimal
    raw_unit: str | None
    raw_range: str | None
    range_low: Decimal | None  # in printed units
    range_high: Decimal | None
    flag: str | None  # "H", "L" or None
    qualifier: str | None  # "<" or ">" when the value is printed as a limit
    section: str | None  # panel code of the enclosing section, if recognised
    page: int
    bbox: tuple[float, float, float, float]  # x0, top, x1, bottom (points)
    confidence: float  # lowest OCR confidence among the row's tokens (1.0 for text layer)


@dataclass
class ExtractionResult:
    pages: list[Page]
    rows: list[ParsedRow]
    lab_name: str | None = None
    collected_at: date | None = None  # sample collection date read from the header
