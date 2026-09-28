"""Extraction entry point: file bytes → pages → lines → parsed result rows."""

from __future__ import annotations

from app.catalogue.data import CatalogueData
from app.catalogue.units import normalize_unit
from app.extraction.dates import find_collection_date
from app.extraction.document import load_pages
from app.extraction.layout import group_lines
from app.extraction.ocr import OCREngine, default_engine
from app.extraction.parser import detect_section, parse_line
from app.extraction.types import ExtractionResult, ParsedRow


def known_unit_keys(catalogue: CatalogueData) -> set[str]:
    """Every normalised unit the catalogue can interpret, plus common unitless spellings."""
    keys = {normalize_unit(t.unit) for t in catalogue.tests}
    keys |= {normalize_unit(c.from_unit) for c in catalogue.conversions}
    keys.discard("")
    return keys


def extract(data: bytes, mime: str, catalogue: CatalogueData, ocr: OCREngine | None = None,
            force_ocr: bool = False) -> ExtractionResult:
    pages = load_pages(data, mime, ocr or _LazyOCR(), force_ocr=force_ocr)
    units = known_unit_keys(catalogue)
    rows: list[ParsedRow] = []
    lab_name: str | None = None
    section: str | None = None
    header: list[str] = []
    for page in pages:
        for line in group_lines(page.tokens):
            if page.number == 0:
                header.append(line.text)
            if lab_name is None and page.number == 0 and line.tokens and line.text.strip():
                lab_name = line.text.strip()
            found = detect_section(line)
            if found:
                section = found
                continue
            row = parse_line(line, page.number, section, units)
            if row is not None:
                rows.append(row)
    return ExtractionResult(pages, rows, lab_name, find_collection_date(header))


class _LazyOCR:
    """Defers loading OCR models until a page actually needs OCR."""

    def read(self, image):  # noqa: ANN001, ANN201 - matches OCREngine
        return default_engine().read(image)
