"""End-to-end extraction against the committed synthetic samples (data/synthetic/samples)."""

from pathlib import Path

import pytest

from app.catalogue import CatalogueData
from app.core.config import settings
from tools.eval.extraction import evaluate

SAMPLES = Path(settings.data_dir) / "synthetic" / "samples"


def test_text_layer_is_exact(catalogue: CatalogueData) -> None:
    summary = evaluate(SAMPLES, "text")["all"]
    assert summary["recall"] == 1.0 and summary["precision"] == 1.0
    for field in ("name", "value", "unit", "range", "flag"):
        assert summary[f"{field}_acc"] == 1.0, field


@pytest.mark.slow
def test_ocr_reads_a_rendered_report(catalogue: CatalogueData) -> None:
    summary = evaluate(SAMPLES, "ocr", limit=1)["all"]
    assert summary["recall"] >= 0.9
    assert summary["precision"] >= 0.98
    assert summary["value_acc"] >= 0.97
