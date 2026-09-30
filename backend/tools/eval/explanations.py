"""Live evaluation of explanations (docs/11 §4): how often the model's text is shown, why the template is used
otherwise, latency, tokens, cost and readability.

    python -m tools.eval.explanations --profile "Explanation eval" --languages en,hi \
        --out /srv/data/eval/explanations.jsonl

Each report and language runs through the real pipeline (Groq, E5 retrieval, validator, judge) inside a transaction
that is rolled back, with external-AI consent granted only inside it, so nothing is stored. Every outcome, including
rejected text and the reasons, is written to --out for the clinical and native-speaker reviews.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from collections import Counter
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.db import SessionLocal
from app.explain.llm import GroqProvider
from app.knowledge.embed import default_embedder
from app.models import Consent, Profile, Report
from app.models.enums import ConsentPurpose, ReportStatus
from app.services.explanation import explain_report

# USD per token, Groq's list price for openai/gpt-oss-120b; check groq.com/pricing before quoting.
PRICE_IN = 0.15 / 1_000_000
PRICE_OUT = 0.60 / 1_000_000


def syllables(word: str) -> int:
    word = word.lower()
    groups = re.findall(r"[aeiouy]+", word)
    n = len(groups) - (1 if word.endswith("e") and len(groups) > 1 else 0)
    return max(1, n)


def fk_grade(text: str) -> float | None:
    """Flesch–Kincaid grade level (English)."""
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    words = re.findall(r"[A-Za-z']+", text)
    if not sentences or not words:
        return None
    return 0.39 * len(words) / len(sentences) + 11.8 * sum(map(syllables, words)) / len(words) - 15.59


def english_text(content: dict) -> str:
    parts = [content.get("summary", "")]
    for t in content.get("per_test", []):
        parts += [t.get("what_it_measures", ""), t.get("what_this_result_means", "")]
    return " ".join(parts)


def evaluate(profile_name: str, languages: list[str], limit: int, pause: float, out: Path) -> dict:
    provider = GroqProvider(settings.groq_api_key, settings.llm_model)
    embedder = default_embedder()
    with SessionLocal() as s:
        ids = s.scalars(
            select(Report.id).join(Profile, Profile.id == Report.profile_id)
            .where(Profile.display_name == profile_name, Report.deleted_at.is_(None),
                   Report.status.in_([ReportStatus.EXPLAINING, ReportStatus.EXPLAINED]))
            .order_by(Report.created_at).limit(limit)).all()
    records = []
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for rid in ids:
            for lang in languages:
                s = SessionLocal()
                try:
                    report = s.get(Report, rid)
                    profile = s.get(Profile, report.profile_id)
                    s.add(Consent(user_id=profile.owner_user_id, profile_id=profile.id,
                                  purpose=ConsentPurpose.EXTERNAL_AI, policy_version="eval"))
                    s.flush()
                    o = explain_report(s, report, lang, provider, embedder)
                    e = o.explanation
                    rec = {
                        "report_id": str(rid), "language": lang, "source": o.source, "reason": o.reason,
                        "problems": [p.code for p in o.problems], "details": [p.detail for p in o.problems],
                        "latency_ms": e.latency_ms, "input_tokens": e.input_tokens, "output_tokens": e.output_tokens,
                        "focus": e.content["meta"]["focus"],
                        "grade": fk_grade(english_text(e.content)) if lang == "en" and o.source == "model" else None,
                        "shown": {k: e.content.get(k) for k in ("summary", "per_test", "doctor_questions", "sources")},
                        "rejected": o.rejected,
                    }
                finally:
                    s.rollback()
                    s.close()
                records.append(rec)
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
                print(f"{str(rid)[:8]} {lang} {rec['source']:8} {rec['reason'] or '':15} "
                      f"{','.join(rec['problems']):20} {rec['latency_ms'] or 0:>6} ms "
                      f"{rec['input_tokens'] or 0:>5}/{rec['output_tokens'] or 0:<5} tokens", flush=True)
                time.sleep(pause)
    return summarise(records)


def summarise(records: list[dict]) -> dict:
    out: dict = {"explanations": len(records)}
    for lang in sorted({r["language"] for r in records}):
        rs = [r for r in records if r["language"] == lang]
        called = [r for r in rs if r["input_tokens"]]
        grades = [r["grade"] for r in rs if r["grade"] is not None]
        latencies = sorted(r["latency_ms"] for r in called)
        out[lang] = {
            "n": len(rs),
            "shown_from_model": round(sum(r["source"] == "model" for r in rs) / len(rs), 3),
            "template_reasons": dict(Counter(r["reason"] for r in rs if r["source"] == "template")),
            "problem_codes": dict(Counter(c for r in rs for c in r["problems"])),
            "latency_ms_p50": statistics.median(latencies) if latencies else None,
            "latency_ms_max": latencies[-1] if latencies else None,
            "tokens_in_mean": round(statistics.mean(r["input_tokens"] for r in called)) if called else None,
            "tokens_out_mean": round(statistics.mean(r["output_tokens"] for r in called)) if called else None,
            "cost_usd_mean": round(statistics.mean(r["input_tokens"] * PRICE_IN + r["output_tokens"] * PRICE_OUT
                                                   for r in called), 5) if called else None,
            "fk_grade_mean": round(statistics.mean(grades), 1) if grades else None,
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m tools.eval.explanations")
    ap.add_argument("--profile", default="Explanation eval")
    ap.add_argument("--languages", default="en,hi")
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--pause", type=float, default=20.0, help="seconds between explanations (rate limits)")
    ap.add_argument("--out", default=str(Path(settings.data_dir) / "eval" / "explanations.jsonl"))
    a = ap.parse_args()
    summary = evaluate(a.profile, a.languages.split(","), a.limit, a.pause, Path(a.out))
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    Path(a.out).with_suffix(".summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False),
                                                         encoding="utf-8")


if __name__ == "__main__":
    main()
