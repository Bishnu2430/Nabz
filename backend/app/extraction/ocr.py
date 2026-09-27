"""OCR engines. RapidOCR runs PaddleOCR detection/recognition models on ONNX Runtime (CPU)."""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol

import numpy as np

from app.extraction.types import Token


class OCREngine(Protocol):
    def read(self, image: np.ndarray) -> list[Token]:
        """Text lines with boxes in image pixels."""
        ...


class RapidOCREngine:
    def __init__(self) -> None:
        from rapidocr_onnxruntime import RapidOCR  # heavy import, loaded on first use

        self._engine = RapidOCR()

    def read(self, image: np.ndarray) -> list[Token]:
        # Pages are deskewed before OCR; the line-orientation classifier then does more harm than
        # good (it flips some upright lines, turning "mg/dl" into "Ip/6w").
        result, _ = self._engine(image, use_cls=False)
        tokens: list[Token] = []
        for box, text, score in result or []:
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            tokens.append(Token(text.strip(), min(xs), min(ys), max(xs), max(ys), float(score)))
        return [t for t in tokens if t.text]


@lru_cache(maxsize=1)
def default_engine() -> RapidOCREngine:
    """One engine per process; model loading takes a few seconds."""
    return RapidOCREngine()
