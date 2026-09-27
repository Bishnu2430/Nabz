"""Train the row-confidence model (docs/03 §8) on synthetic reports read by OCR.

    python -m tools.train.confidence                  # train on train/, evaluate on eval/
    python -m tools.train.confidence --out /srv/data/models/confidence-v1.json

A row is labelled correct when it matches a ground-truth row AND its test, value,
unit and canonical value are all right; parser output with no ground-truth row
is labelled wrong. Training uses OCR, simulated-photo and some text-layer
reports; evaluation uses a separate report set. Coefficients are saved as JSON
(no pickles), and app.extraction.interpret.ConfidenceModel applies them.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from app.catalogue import read_catalogue
from app.core.config import settings
from app.extraction.interpret import FEATURES, ConfidenceModel
from tools.eval.extraction import build_interpreter, fields_ok, iter_reports, match_rows, raw_row

TARGET_RECALL = 0.90  # share of wrong rows that must fall below the threshold (docs/11 §4)
# The probabilities are calibrated (ECE < 0.01), so the threshold can be read as a policy: a row with more than a
# 10 % chance of being wrong is always shown for checking, even when fewer flags would meet TARGET_RECALL.
MIN_THRESHOLD = 0.90


def collect(directory: Path, modes: dict[str, int | None]) -> tuple[np.ndarray, np.ndarray]:
    interp = build_interpreter(read_catalogue(Path(settings.data_dir) / "catalogue"))
    xs, ys = [], []
    for mode, limit in modes.items():
        for truth, ex in iter_reports(directory, mode, limit):
            p = truth["persona"]
            matched = {id(r): g for g, r in match_rows(truth["rows"], ex.rows)}
            for r in ex.rows:
                it = interp.interpret(raw_row(r, ex.sources), p["sex"], p["age"])
                g = matched.get(id(r))
                ok = g is not None and all(v for k, v in fields_ok(g, r, it.test_code, it.value_num).items()
                                           if k in ("test", "value", "unit", "canonical"))
                xs.append([it.features[f] for f in FEATURES])
                ys.append(1 if ok else 0)
    return np.array(xs, dtype=float), np.array(ys, dtype=int)


def ece(p: np.ndarray, y: np.ndarray, bins: int = 10) -> float:
    """Expected calibration error."""
    edges = np.linspace(0, 1, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        mask = (p >= lo) & ((p < hi) if hi < 1 else (p <= hi))
        if mask.any():
            total += mask.mean() * abs(p[mask].mean() - y[mask].mean())
    return float(total)


def pick_threshold(p: np.ndarray, y: np.ndarray, recall: float) -> float:
    """Lowest threshold whose flagged set (p < τ) still catches `recall` of the wrong rows."""
    wrong = p[y == 0]
    if len(wrong) == 0:
        return 0.5
    return float(np.quantile(wrong, recall)) + 1e-6


def report(name: str, p: np.ndarray, y: np.ndarray, tau: float) -> dict[str, float]:
    flagged = p < tau
    wrong = y == 0
    m = {
        "rows": int(len(y)), "wrong_rows": int(wrong.sum()),
        "auc": float(roc_auc_score(y, p)) if 0 < y.sum() < len(y) else float("nan"),
        "ece": ece(p, y),
        "recall_of_wrong_rows": float((flagged & wrong).sum() / max(wrong.sum(), 1)),
        "flagged_share": float(flagged.mean()),
    }
    print(f"{name:<6} rows={m['rows']:<5} wrong={m['wrong_rows']:<4} auc={m['auc']:.3f} ece={m['ece']:.3f} "
          f"wrong-caught={m['recall_of_wrong_rows']:.3f} flagged={m['flagged_share']:.3f}")
    return m


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m tools.train.confidence")
    base = Path(settings.data_dir) / "synthetic"
    ap.add_argument("--train", default=str(base / "train"))
    ap.add_argument("--eval", default=str(base / "eval"))
    ap.add_argument("--eval-limit", type=int, default=30)
    ap.add_argument("--out", default=str(Path(settings.data_dir) / "models" / "confidence-v1.json"))
    a = ap.parse_args()

    x_train, y_train = collect(Path(a.train), {"photo": None, "ocr": None, "text": 15})
    x_eval, y_eval = collect(Path(a.eval), {"photo": a.eval_limit, "ocr": a.eval_limit})
    model = LogisticRegression(C=1.0, max_iter=2000).fit(x_train, y_train)
    p_train = model.predict_proba(x_train)[:, 1]
    p_eval = model.predict_proba(x_eval)[:, 1]
    tau = max(pick_threshold(p_train, y_train, TARGET_RECALL), MIN_THRESHOLD)
    metrics = {"train": report("train", p_train, y_train, tau), "eval": report("eval", p_eval, y_eval, tau)}
    # The hand-set weights the app used before this model existed, on the same held-out rows.
    hand = ConfidenceModel()
    p_hand = np.array([hand.predict(dict(zip(FEATURES, row, strict=True))) for row in x_eval])
    metrics["eval_hand_weights"] = report("hand", p_hand, y_eval, hand.threshold)

    params = {
        "version": f"v1-{date.today().isoformat()}",
        "intercept": float(model.intercept_[0]),
        "weights": {f: float(w) for f, w in zip(FEATURES, model.coef_[0], strict=True)},
        "threshold": round(tau, 4),
        "target_recall_of_wrong_rows": TARGET_RECALL,
        "metrics": metrics,
        "trained_on": {"train_dir": a.train, "eval_dir": a.eval, "modes": ["photo", "ocr", "text(15)"]},
    }
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(params, indent=2), encoding="utf-8")
    print(f"threshold τ = {tau:.3f}; wrote {out}")
    for f, w in params["weights"].items():
        print(f"  {f:<14} {w:+.3f}")


if __name__ == "__main__":
    main()
