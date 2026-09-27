"""Image pre-processing: skew correction and a simple quality score (FR-07)."""

from __future__ import annotations

import cv2
import numpy as np

MAX_DESKEW_DEGREES = 15.0


def _gray(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if image.ndim == 3 else image


def estimate_skew(image: np.ndarray, max_angle: float = MAX_DESKEW_DEGREES) -> float:
    """Degrees to rotate the image (counter-clockwise positive) so text lines become horizontal.

    Projection-profile search: when text lines are horizontal, the row sums of ink form sharp
    peaks and valleys, so their variance is highest. A coarse search is refined around the best
    angle. Works on a downscaled, binarised copy and returns 0.0 when the page has no clear lines.
    """
    gray = _gray(image)
    scale = 900 / max(gray.shape)
    if scale < 1:
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    h, w = binary.shape
    centre = (w / 2, h / 2)

    def score(angle: float) -> float:
        m = cv2.getRotationMatrix2D(centre, angle, 1.0)
        rotated = cv2.warpAffine(binary, m, (w, h), flags=cv2.INTER_NEAREST, borderValue=0)
        return float(np.var(rotated.sum(axis=1, dtype=np.float64)))

    coarse = np.arange(-max_angle, max_angle + 1e-6, 0.5)
    scores = [score(a) for a in coarse]
    best = float(coarse[int(np.argmax(scores))])
    fine = np.arange(best - 0.5, best + 0.5 + 1e-6, 0.05)
    best = float(fine[int(np.argmax([score(a) for a in fine]))])
    flat = score(0.0)
    # Only trust the estimate if it is clearly better than leaving the page as it is.
    return best if flat == 0 or score(best) > flat * 1.02 else 0.0


def deskew(image: np.ndarray) -> tuple[np.ndarray, float]:
    angle = estimate_skew(image)
    if abs(angle) < 0.2:
        return image, 0.0
    h, w = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    rotated = cv2.warpAffine(image, matrix, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return rotated, angle


def quality_score(image: np.ndarray) -> float:
    """0–1: sharpness (variance of the Laplacian) combined with exposure."""
    gray = _gray(image)
    scale = 1000 / max(gray.shape)
    if scale < 1:
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    sharpness = min(cv2.Laplacian(gray, cv2.CV_64F).var() / 800.0, 1.0)
    mean = float(gray.mean()) / 255
    exposure = 1.0 - min(abs(mean - 0.75) / 0.5, 1.0)
    return round(0.7 * sharpness + 0.3 * exposure, 3)
