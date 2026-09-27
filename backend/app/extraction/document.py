"""Turn an uploaded file into pages of positioned text tokens.

Digital PDFs carry an exact text layer, which is used directly. Scanned PDFs
and photos are rendered to images and read with OCR.
"""

from __future__ import annotations

import io

import numpy as np
import pypdfium2 as pdfium
from PIL import Image, ImageOps

from app.extraction.ocr import OCREngine
from app.extraction.preprocess import deskew, quality_score
from app.extraction.types import Page, Token

OCR_DPI = 200
MIN_TEXT_CHARS = 40  # below this a PDF page is treated as scanned
PDF_MIME = "application/pdf"
IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp"}


def load_pages(data: bytes, mime: str, ocr: OCREngine, force_ocr: bool = False) -> list[Page]:
    if mime == PDF_MIME:
        return _pdf_pages(data, ocr, force_ocr)
    if mime in IMAGE_MIMES:
        image = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
        return [_ocr_page(0, np.asarray(image), ocr, dpi=None)]
    raise ValueError(f"unsupported file type: {mime}")


def _pdf_pages(data: bytes, ocr: OCREngine, force_ocr: bool) -> list[Page]:
    pdf = pdfium.PdfDocument(data)
    pages: list[Page] = []
    try:
        for i in range(len(pdf)):
            page = pdf[i]
            width, height = page.get_size()
            tokens = [] if force_ocr else _text_layer_tokens(page, height)
            if sum(len(t.text) for t in tokens) >= MIN_TEXT_CHARS:
                pages.append(Page(i, width, height, "text-layer", tokens))
            else:
                image = page.render(scale=OCR_DPI / 72).to_numpy()
                pages.append(_ocr_page(i, image, ocr, dpi=OCR_DPI, size_pt=(width, height)))
    finally:
        pdf.close()
    return pages


def _text_layer_tokens(page: pdfium.PdfPage, page_height: float) -> list[Token]:
    """One token per text run (PDFium text rectangle)."""
    textpage = page.get_textpage()
    tokens: list[Token] = []
    try:
        for i in range(textpage.count_rects()):
            left, bottom, right, top = textpage.get_rect(i)
            text = textpage.get_text_bounded(left, bottom, right, top).strip()
            if text:
                tokens.append(Token(text, left, page_height - top, right, page_height - bottom))
    finally:
        textpage.close()
    return tokens


def _ocr_page(number: int, image: np.ndarray, ocr: OCREngine, dpi: int | None,
              size_pt: tuple[float, float] | None = None) -> Page:
    image, angle = deskew(image)
    quality = quality_score(image)
    # Photos have no physical size: treat them as 150 dpi so coordinates stay in a familiar range.
    scale = (dpi or 150) / 72
    h_px, w_px = image.shape[:2]
    width, height = size_pt or (w_px / scale, h_px / scale)
    tokens = [Token(t.text, t.x0 / scale, t.top / scale, t.x1 / scale, t.bottom / scale, t.conf)
              for t in ocr.read(image)]
    return Page(number, width, height, "ocr", tokens, quality, angle)
