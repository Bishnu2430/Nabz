"""Render a report page for the review screen, in the same geometry as its stored boxes."""

from __future__ import annotations

import io

import numpy as np
import pypdfium2 as pdfium
from PIL import Image, ImageOps

from app.extraction.preprocess import deskew, rotate

DISPLAY_DPI = 150
MAX_SIDE = 1800  # px; boxes are drawn as fractions of the page, so the display size is free to change


def render_page(data: bytes, mime: str, page_no: int, source: str, skew: float | None = None) -> tuple[bytes, str]:
    """(image bytes, media type) for one page.

    OCR'd pages are rotated by the angle stored at extraction (`skew`) so stored boxes line up;
    pages extracted before the angle was stored fall back to estimating it again.
    Photos go out as JPEG and rendered PDF pages as PNG, both scaled to at most MAX_SIDE.
    """
    if mime == "application/pdf":
        pdf = pdfium.PdfDocument(data)
        try:
            if not 0 <= page_no < len(pdf):
                raise IndexError(page_no)
            image = pdf[page_no].render(scale=DISPLAY_DPI / 72).to_numpy()
        finally:
            pdf.close()
    else:
        if page_no != 0:
            raise IndexError(page_no)
        image = np.asarray(ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB"))
    if source == "ocr":
        image = rotate(image, skew) if skew is not None else deskew(image)[0]

    out = Image.fromarray(image)
    out.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    if mime == "application/pdf":
        out.save(buf, format="PNG")
        return buf.getvalue(), "image/png"
    out.convert("RGB").save(buf, format="JPEG", quality=85, progressive=True)
    return buf.getvalue(), "image/jpeg"
