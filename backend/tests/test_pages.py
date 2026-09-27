"""Page rendering for the review screen."""

from __future__ import annotations

import io

import numpy as np
from PIL import Image

from app.services.pages import MAX_SIDE, render_page


def _photo(w: int, h: int) -> bytes:
    rng = np.random.default_rng(3)
    buf = io.BytesIO()
    Image.fromarray(rng.integers(0, 255, (h, w, 3), dtype=np.uint8)).save(buf, format="JPEG")
    return buf.getvalue()


def test_photo_is_scaled_and_sent_as_jpeg() -> None:
    data, media_type = render_page(_photo(3000, 4000), "image/jpeg", 0, "ocr", skew=0.0)
    assert media_type == "image/jpeg"
    image = Image.open(io.BytesIO(data))
    assert max(image.size) == MAX_SIDE
    assert image.size[0] / image.size[1] == 0.75  # aspect kept, so fractional boxes still line up


def test_stored_skew_is_applied_without_re_estimating(monkeypatch) -> None:
    import app.services.pages as pages

    def boom(_image):
        raise AssertionError("deskew should not run when the angle is stored")

    monkeypatch.setattr(pages, "deskew", boom)
    data, _ = render_page(_photo(400, 600), "image/png", 0, "ocr", skew=2.5)
    assert Image.open(io.BytesIO(data)).size == (400, 600)
