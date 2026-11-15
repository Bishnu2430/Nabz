"""The embedding model download (`python -m tools.knowledge model`): pinned files, checked before they are used."""

import hashlib
from pathlib import Path

import pytest

from tools.knowledge.__main__ import MODEL_FILES, download_model


def test_the_pinned_files_are_the_ones_the_embedder_reads() -> None:
    names = [name for name, _, _ in MODEL_FILES]
    assert {"tokenizer.json", "onnx/model_quantized.onnx"} <= set(names)
    assert all("/resolve/main/" not in url and url.startswith("https://") for _, url, _ in MODEL_FILES)


def test_a_file_is_installed_only_when_its_checksum_matches(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"model bytes")
    good = hashlib.sha256(b"model bytes").hexdigest()
    target = tmp_path / "model"

    with pytest.raises(SystemExit):
        download_model(target, [("onnx/model.onnx", source.as_uri(), "0" * 64)])
    assert not any(target.rglob("*.onnx*"))

    download_model(target, [("onnx/model.onnx", source.as_uri(), good)])
    assert (target / "onnx" / "model.onnx").read_bytes() == b"model bytes"
    download_model(target, [("onnx/model.onnx", "https://unreachable.invalid/x", good)])  # already there: no download
