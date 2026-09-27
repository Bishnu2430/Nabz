"""Measure extraction and interpretation against synthetic ground truth (docs/11 §4).

    python -m tools.eval.extraction --dir /srv/data/synthetic/samples --mode text
    python -m tools.eval.extraction --dir ... --mode ocr      # render pages, then OCR
    python -m tools.eval.extraction --dir ... --mode photo    # + rotation, blur, noise, JPEG

Rows are matched to ground truth by page and vertical position. Field accuracy
is reported over matched rows, recall and precision over all rows. `test` is the
catalogue mapping and `canonical` the value after unit conversion. OCR results
are cached per report and mode (`<dir>/.cache/<mode>/`), so repeated runs and
confidence-model training don't redo the OCR.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from pathlib import Path

import cv2
import numpy as np
import pypdfium2 as pdfium

from app.catalogue import CatalogueData, read_catalogue
from app.catalogue.convert import UnitConverter
from app.catalogue.matcher import CatalogueMatcher
from app.catalogue.units import normalize_unit
from app.core.config import settings
from app.extraction import extract, known_unit_keys
from app.extraction.document import OCR_DPI, _ocr_page
from app.extraction.interpret import ConfidenceModel, Interpreter, RawRow
from app.extraction.layout import group_lines
from app.extraction.ocr import default_engine
from app.extraction.parser import detect_section, parse_line, parse_range
from app.extraction.types import ParsedRow

FIELDS = ("name", "value", "unit", "range", "flag", "test", "canonical")


@dataclass
class Extracted:
    rows: list[ParsedRow]
    sources: list[str]  # per page: "text-layer" or "ocr"
    seconds: float


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
        out = {"rows": self.gt, "recall": self.matched / self.gt if self.gt else 0.0,
               "precision": self.matched / self.parsed if self.parsed else 0.0}
        for f in FIELDS:
            out[f"{f}_acc"] = self.correct[f] / self.matched if self.matched else 0.0
        out["seconds"] = self.seconds
        return out


def build_interpreter(cat: CatalogueData, model: ConfidenceModel | None = None) -> Interpreter:
    conv = UnitConverter(cat)
    return Interpreter(cat, CatalogueMatcher(cat, conv), conv, model)


def degrade(image: np.ndarray, rng: random.Random) -> np.ndarray:
    """Emulate a phone photo: slight rotation, blur, uneven light, noise and JPEG compression."""
    h, w = image.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), rng.uniform(-2.5, 2.5), 1.0)
    img = cv2.warpAffine(image, m, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(235, 235, 230))
    img = cv2.GaussianBlur(img, (0, 0), rng.uniform(0.6, 1.3))
    shade = np.linspace(rng.uniform(0.8, 0.95), 1.0, w, dtype=np.float32)[None, :, None]
    noise = np.random.default_rng(rng.randint(0, 9999)).normal(0, 6, img.shape)
    img = np.clip(img.astype(np.float32) * shade + noise, 0, 255).astype(np.uint8)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, rng.randint(55, 80)])
    return cv2.imdecode(buf, cv2.IMREAD_COLOR) if ok else img


_degrade = degrade  # backwards-compatible name used by older scripts


def _extract_photo(pdf_bytes: bytes, units: set[str], rng: random.Random) -> tuple[list[ParsedRow], list[str]]:
    pdf = pdfium.PdfDocument(pdf_bytes)
    rows: list[ParsedRow] = []
    section = None
    for i in range(len(pdf)):
        w, h = pdf[i].get_size()
        image = degrade(pdf[i].render(scale=OCR_DPI / 72).to_numpy(), rng)
        page = _ocr_page(i, image, default_engine(), dpi=OCR_DPI, size_pt=(w, h))
        for line in group_lines(page.tokens):
            found = detect_section(line)
            if found:
                section = found
                continue
            if (row := parse_line(line, i, section, units)) is not None:
                rows.append(row)
    n = len(pdf)
    pdf.close()
    return rows, ["ocr"] * n


def _row_to_json(r: ParsedRow) -> dict:
    d = asdict(r)
    for k in ("value", "range_low", "range_high"):
        d[k] = None if d[k] is None else str(d[k])
    return d


def _row_from_json(d: dict) -> ParsedRow:
    for k in ("value", "range_low", "range_high"):
        d[k] = None if d[k] is None else Decimal(d[k])
    d["bbox"] = tuple(d["bbox"])
    return ParsedRow(**d)


def extract_cached(directory: Path, truth: dict, mode: str, cat: CatalogueData, units: set[str],
                   seed: int = 1, use_cache: bool = True) -> Extracted:
    cache = directory / ".cache" / f"{mode}-{seed}" / f"{truth['id']}.json"
    if use_cache and mode != "text" and cache.exists():
        d = json.loads(cache.read_text(encoding="utf-8"))
        return Extracted([_row_from_json(r) for r in d["rows"]], d["sources"], d["seconds"])
    data = (directory / f"{truth['id']}.pdf").read_bytes()
    start = time.perf_counter()
    if mode == "photo":
        rows, sources = _extract_photo(data, units, random.Random(f"{seed}:{truth['id']}"))
    else:
        result = extract(data, "application/pdf", cat, force_ocr=(mode == "ocr"))
        rows, sources = result.rows, [p.source for p in result.pages]
    out = Extracted(rows, sources, time.perf_counter() - start)
    if mode != "text":
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"rows": [_row_to_json(r) for r in rows], "sources": sources,
                                     "seconds": out.seconds}), encoding="utf-8")
    return out


def match_rows(gt_rows: list[dict], rows: list[ParsedRow]) -> list[tuple[dict, ParsedRow]]:
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


_match = match_rows  # backwards-compatible name


def squash_name(text: str) -> str:
    return "".join(text.split()).casefold()


def raw_row(r: ParsedRow, sources: list[str]) -> RawRow:
    return RawRow(r.raw_name, r.raw_value, r.raw_unit, r.raw_range, r.flag, r.section, r.confidence,
                  sources[r.page] if r.page < len(sources) else "ocr")


def fields_ok(g: dict, r: ParsedRow, test_code: str | None = None, value_num: Decimal | None = None) -> dict:
    gt_range = parse_range(g["printed_range"]) if g["printed_range"] else None
    canon = Decimal(g["value_canonical"])
    return {
        # OCR often drops spaces between words; names are compared ignoring spaces and case,
        # which is also how the catalogue matcher treats them.
        "name": squash_name(g["printed_name"]) == squash_name(r.raw_name),
        "value": Decimal(g["printed_value"].replace(",", "")) == r.value,
        "unit": normalize_unit(g["printed_unit"]) == normalize_unit(r.raw_unit),
        "range": (gt_range or (None, None)) == (r.range_low, r.range_high),
        "flag": (g["flag"] or None) == r.flag,
        "test": test_code == g["test_code"],
        "canonical": value_num is not None and abs(value_num - canon) <= max(Decimal("0.01"), abs(canon) / 1000),
    }


_fields_ok = fields_ok  # backwards-compatible name


def truth_files(directory: Path, limit: int | None = None) -> list[Path]:
    return [f for f in sorted(directory.glob("*.json")) if f.name.startswith(("syn-", "hist-"))][:limit]


def iter_reports(directory: Path, mode: str, limit: int | None = None, seed: int = 1
                 ) -> Iterator[tuple[dict, Extracted]]:
    cat = read_catalogue(Path(settings.data_dir) / "catalogue")
    units = known_unit_keys(cat)
    for jf in truth_files(directory, limit):
        truth = json.loads(jf.read_text(encoding="utf-8"))
        yield truth, extract_cached(directory, truth, mode, cat, units, seed)


def evaluate(directory: Path, mode: str, limit: int | None = None, seed: int = 1,
             verbose: bool = False) -> dict[str, dict[str, float]]:
    cat = read_catalogue(Path(settings.data_dir) / "catalogue")
    interp = build_interpreter(cat)
    by_layout: dict[str, Score] = defaultdict(Score)
    for truth, ex in iter_reports(directory, mode, limit, seed):
        s = Score(gt=len(truth["rows"]), parsed=len(ex.rows), seconds=ex.seconds)
        p = truth["persona"]
        for g, r in match_rows(truth["rows"], ex.rows):
            s.matched += 1
            it = interp.interpret(raw_row(r, ex.sources), p["sex"], p["age"])
            for f, ok in fields_ok(g, r, it.test_code, it.value_num).items():
                s.correct[f] += ok
                if verbose and not ok:
                    print(f"  {truth['id']} {g['test_code']:<16} {f:<9} gt={g['printed_name']!r} "
                          f"{g['printed_value']} {g['printed_unit']!r}  got={r.raw_name!r} {r.raw_value} "
                          f"{r.raw_unit!r} → {it.test_code}")
        by_layout[truth["layout"]].add(s)
        by_layout["all"].add(s)
    return {k: v.summary() for k, v in sorted(by_layout.items())}


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m tools.eval.extraction")
    ap.add_argument("--dir", default=str(Path(settings.data_dir) / "synthetic" / "samples"))
    ap.add_argument("--mode", choices=["text", "ocr", "photo"], default="text")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--out", help="write the summary as JSON")
    a = ap.parse_args()
    summary = evaluate(Path(a.dir), a.mode, a.limit, a.seed, verbose=a.verbose)
    cols = ["rows", "recall", "precision", *(f"{f}_acc" for f in FIELDS), "seconds"]
    print(f"mode={a.mode}  dir={a.dir}")
    print(f"{'layout':<9}" + "".join(f"{c.replace('_acc', ''):>10}" for c in cols))
    for layout, m in summary.items():
        print(f"{layout:<9}" + "".join(f"{m[c]:>10.0f}" if c == "rows" else f"{m[c]:>10.3f}" for c in cols))
    if a.out:
        Path(a.out).write_text(json.dumps({"mode": a.mode, "summary": summary}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
