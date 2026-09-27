"""Measure extraction against synthetic ground truth (docs/11 §4).

    python -m tools.eval.extraction --dir /srv/data/synthetic/samples --mode text
    python -m tools.eval.extraction --dir ... --mode ocr      # render pages, then OCR
    python -m tools.eval.extraction --dir ... --mode photo    # + rotation, blur, noise, JPEG

Rows are matched to ground truth by page and vertical position; field accuracy
is reported over matched rows, recall and precision over all rows.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import cv2
import numpy as np
import pypdfium2 as pdfium

from app.catalogue import read_catalogue
from app.catalogue.units import normalize_unit
from app.core.config import settings
from app.extraction import extract, known_unit_keys
from app.extraction.document import OCR_DPI, _ocr_page
from app.extraction.layout import group_lines
from app.extraction.ocr import default_engine
from app.extraction.parser import detect_section, parse_line, parse_range
from app.extraction.types import ExtractionResult, ParsedRow

FIELDS = ("name", "value", "unit", "range", "flag")


@dataclass
class Score:
    gt: int = 0
    parsed: int = 0
    matched: int = 0
    correct: dict[str, int] = field(default_factory=lambda: dict.fromkeys(FIELDS, 0))
    seconds: float = 0.0

    def add(self, other: Score) -> None:
        self.gt += other.gt
        self.parsed += other.parsed
        self.matched += other.matched
        self.seconds += other.seconds
        for f in FIELDS:
            self.correct[f] += other.correct[f]

    def summary(self) -> dict[str, float]:
        out = {
            "rows": self.gt,
            "recall": self.matched / self.gt if self.gt else 0.0,
            "precision": self.matched / self.parsed if self.parsed else 0.0,
        }
        for f in FIELDS:
            out[f"{f}_acc"] = self.correct[f] / self.matched if self.matched else 0.0
        # A row is fully right only if every field is; report the strict end-to-end rate too.
        out["seconds"] = self.seconds
        return out


def _degrade(image: np.ndarray, rng: random.Random) -> np.ndarray:
    """Emulate a phone photo: slight rotation, blur, uneven light, noise and JPEG compression."""
    h, w = image.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), rng.uniform(-2.5, 2.5), 1.0)
    img = cv2.warpAffine(image, m, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(235, 235, 230))
    img = cv2.GaussianBlur(img, (0, 0), rng.uniform(0.6, 1.3))
    shade = np.linspace(rng.uniform(0.8, 0.95), 1.0, w, dtype=np.float32)[None, :, None]
    img = np.clip(img.astype(np.float32) * shade + np.random.default_rng(rng.randint(0, 9999)).normal(0, 6, img.shape),
                  0, 255).astype(np.uint8)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, rng.randint(55, 80)])
    return cv2.imdecode(buf, cv2.IMREAD_COLOR) if ok else img


def _extract_photo(pdf_bytes: bytes, units: set[str], rng: random.Random) -> ExtractionResult:
    pdf = pdfium.PdfDocument(pdf_bytes)
    pages, rows, section = [], [], None
    for i in range(len(pdf)):
        w, h = pdf[i].get_size()
        image = _degrade(pdf[i].render(scale=OCR_DPI / 72).to_numpy(), rng)
        page = _ocr_page(i, image, default_engine(), dpi=OCR_DPI, size_pt=(w, h))
        pages.append(page)
        for line in group_lines(page.tokens):
            found = detect_section(line)
            if found:
                section = found
                continue
            if (row := parse_line(line, i, section, units)) is not None:
                rows.append(row)
    pdf.close()
    return ExtractionResult(pages, rows)


def _match(gt_rows: list[dict], rows: list[ParsedRow]) -> list[tuple[dict, ParsedRow]]:
    pairs, used = [], set()
    for g in gt_rows:
        gy = (g["bbox"][1] + g["bbox"][3]) / 2
        best, best_d = None, 7.0  # points
        for i, r in enumerate(rows):
            if i in used or r.page != g["page"]:
                continue
            d = abs((r.bbox[1] + r.bbox[3]) / 2 - gy)
            if d < best_d:
                best, best_d = i, d
        if best is not None:
            used.add(best)
            pairs.append((g, rows[best]))
    return pairs


def _squash(text: str) -> str:
    return "".join(text.split()).casefold()


def _fields_ok(g: dict, r: ParsedRow) -> dict[str, bool]:
    gt_range = parse_range(g["printed_range"]) if g["printed_range"] else None
    return {
        # OCR often drops spaces between words; names are compared ignoring spaces and case,
        # which is also how the catalogue matcher treats them.
        "name": _squash(g["printed_name"]) == _squash(r.raw_name),
        "value": Decimal(g["printed_value"].replace(",", "")) == r.value,
        "unit": normalize_unit(g["printed_unit"]) == normalize_unit(r.raw_unit),
        "range": (gt_range or (None, None)) == (r.range_low, r.range_high),
        "flag": (g["flag"] or None) == r.flag,
    }


def evaluate(directory: Path, mode: str, limit: int | None = None, seed: int = 1,
             verbose: bool = False) -> dict[str, dict[str, float]]:
    cat = read_catalogue(Path(settings.data_dir) / "catalogue")
    units = known_unit_keys(cat)
    rng = random.Random(seed)
    by_layout: dict[str, Score] = defaultdict(Score)
    files = sorted(directory.glob("*.json"))
    files = [f for f in files if f.name.startswith(("syn-", "hist-"))][:limit]
    for jf in files:
        truth = json.loads(jf.read_text(encoding="utf-8"))
        data = (directory / f"{truth['id']}.pdf").read_bytes()
        start = time.perf_counter()
        if mode == "photo":
            result = _extract_photo(data, units, rng)
        else:
            result = extract(data, "application/pdf", cat, force_ocr=(mode == "ocr"))
        s = Score(gt=len(truth["rows"]), parsed=len(result.rows), seconds=time.perf_counter() - start)
        for g, r in _match(truth["rows"], result.rows):
            s.matched += 1
            for f, ok in _fields_ok(g, r).items():
                s.correct[f] += ok
                if verbose and not ok:
                    print(f"  {truth['id']} {g['test_code']:<16} {f:<6} gt={g}  got={r}")
        by_layout[truth["layout"]].add(s)
        by_layout["all"].add(s)
    return {k: v.summary() for k, v in sorted(by_layout.items())}


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m tools.eval.extraction")
    ap.add_argument("--dir", default=str(Path(settings.data_dir) / "synthetic" / "samples"))
    ap.add_argument("--mode", choices=["text", "ocr", "photo"], default="text")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--out", help="write the summary as JSON")
    a = ap.parse_args()
    summary = evaluate(Path(a.dir), a.mode, a.limit, verbose=a.verbose)
    cols = ["rows", "recall", "precision", *(f"{f}_acc" for f in FIELDS), "seconds"]
    print(f"mode={a.mode}  dir={a.dir}")
    print(f"{'layout':<9}" + "".join(f"{c:>11}" for c in cols))
    for layout, m in summary.items():
        print(f"{layout:<9}" + "".join(f"{m[c]:>11.0f}" if c in ("rows",) else f"{m[c]:>11.3f}" for c in cols))
    if a.out:
        Path(a.out).write_text(json.dumps({"mode": a.mode, "summary": summary}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
