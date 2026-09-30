"""Red-team suite (docs/11 §4, hazards S-03 – S-06, S-08): unsafe text must be rejected for the right reason,
and benign text that merely looks similar must pass. Cases live in data/redteam/cases.jsonl."""

import json
from pathlib import Path

import pytest

from app.core.config import settings
from app.explain.validator import validate
from tests.explain_fixtures import GOOD, GOOD_HI, passages, payload, with_text

CASES = [json.loads(line) for line in
         (Path(settings.data_dir) / "redteam" / "cases.jsonl").read_text(encoding="utf-8").splitlines() if line]


def test_the_suite_is_big_enough() -> None:
    unsafe = [c for c in CASES if c["expect"] == "reject"]
    assert len(CASES) >= 60 and len(unsafe) >= 50
    assert len({c["id"] for c in CASES}) == len(CASES)


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_case(case: dict) -> None:
    base = GOOD_HI if case["language"] == "hi" else GOOD
    content = with_text(case["field"], case["text"], base)
    found = {p.code for p in validate(content, payload(), passages(), case["language"])}
    if case["expect"] == "accept":
        assert found == set(), f"benign text rejected: {found}"
    else:
        assert case["category"] in found, f"expected {case['category']}, got {found or 'nothing'}"
