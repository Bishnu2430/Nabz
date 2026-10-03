"""The red-team suites (docs/11 §4), run on demand from the safety console as well as in the tests.

Explanations: each case adds unsafe (or harmless but similar-looking) text to a good explanation and expects the
deterministic checks to reject it for the right reason, or to let it through. Questions: each case is a question
and the fixed reply it should get, or none when it may be answered. The cases live in data/redteam/.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

from app.core.config import settings
from app.explain.ask import gate
from app.explain.fixtures import GOOD, GOOD_HI, passages, payload, with_text
from app.explain.validator import validate

ROOT = Path(settings.data_dir) / "redteam"


@dataclass(frozen=True)
class CaseResult:
    suite: str  # explanation | question
    id: str
    language: str
    text: str
    expect: str  # explanation: "reject" or "accept"; question: the fixed reply's kind, or "answer"
    category: str  # what should be caught (explanations), or the expected reply (questions)
    found: list[str]
    passed: bool


@lru_cache(maxsize=2)
def _load(name: str) -> tuple[dict, ...]:
    lines = (ROOT / name).read_text(encoding="utf-8").splitlines()
    return tuple(json.loads(line) for line in lines if line.strip())


def explanation_cases() -> tuple[dict, ...]:
    return _load("cases.jsonl")


def question_cases() -> tuple[dict, ...]:
    return _load("questions.jsonl")


def run_explanation_case(case: dict) -> CaseResult:
    content = with_text(case["field"], case["text"], GOOD_HI if case["language"] == "hi" else GOOD)
    found = sorted({p.code for p in validate(content, payload(), passages(), case["language"])})
    passed = not found if case["expect"] == "accept" else case["category"] in found
    return CaseResult("explanation", case["id"], case["language"], case["text"], case["expect"], case["category"],
                      found, passed)


def run_question_case(case: dict) -> CaseResult:
    reply = gate(case["question"])
    passed = reply == (None if case["expect"] == "answer" else case["expect"])
    return CaseResult("question", case["id"], case["language"], case["question"], case["expect"], case["expect"],
                      [reply] if reply else [], passed)


def run_all() -> dict:
    """Every case of both suites, with totals; about a second on a laptop."""
    started = time.perf_counter()
    results = [run_explanation_case(c) for c in explanation_cases()] + [run_question_case(c) for c in question_cases()]
    totals = {}
    for suite in ("explanation", "question"):
        mine = [r for r in results if r.suite == suite]
        totals[suite] = {"cases": len(mine), "passed": sum(r.passed for r in mine)}
    return {"totals": totals, "results": [asdict(r) for r in results],
            "ms": round((time.perf_counter() - started) * 1000)}
