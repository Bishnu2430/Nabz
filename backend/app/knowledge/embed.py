"""Sentence embeddings for retrieval.

E5Embedder runs intfloat/multilingual-e5-small (384 dimensions, 100 languages) as an int8 ONNX export on ONNX Runtime,
which the image already carries for OCR, so no PyTorch is needed. E5 expects "query: " and "passage: " prefixes,
mean pooling over tokens and L2 normalisation. The model files live in data/external/models (see data/external.md).
"""

from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal, Protocol

import numpy as np

from app.core.config import settings
from app.models.knowledge import EMBEDDING_DIM

Kind = Literal["query", "passage"]
MODEL_DIR = "external/models/multilingual-e5-small"


class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str], kind: Kind) -> list[list[float]]: ...


class E5Embedder:
    name = "intfloat/multilingual-e5-small (onnx int8)"

    def __init__(self, model_dir: Path, batch_size: int = 16):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        self.tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
        self.tokenizer.enable_truncation(512)
        self.tokenizer.enable_padding(pad_id=self.tokenizer.token_to_id("<pad>"), pad_token="<pad>")  # noqa: S106
        self.session = ort.InferenceSession(str(model_dir / "onnx" / "model_quantized.onnx"),
                                            providers=["CPUExecutionProvider"])
        self.inputs = {i.name for i in self.session.get_inputs()}
        self.batch_size = batch_size

    def embed(self, texts: list[str], kind: Kind) -> list[list[float]]:
        out: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = self.tokenizer.encode_batch([f"{kind}: {t}" for t in texts[start:start + self.batch_size]])
            ids = np.array([e.ids for e in batch], dtype=np.int64)
            mask = np.array([e.attention_mask for e in batch], dtype=np.int64)
            feed = {"input_ids": ids, "attention_mask": mask}
            if "token_type_ids" in self.inputs:
                feed["token_type_ids"] = np.zeros_like(ids)
            hidden = self.session.run(None, feed)[0]
            pooled = (hidden * mask[..., None]).sum(axis=1) / np.maximum(mask.sum(axis=1, keepdims=True), 1)
            pooled /= np.linalg.norm(pooled, axis=1, keepdims=True)
            out.extend(pooled.astype(float).tolist())
        return out


class HashEmbedder:
    """Deterministic bag-of-words vectors for tests: texts sharing words are close, and no model is needed."""

    name = "hash-bow (tests)"

    def embed(self, texts: list[str], kind: Kind) -> list[list[float]]:
        out = []
        for text in texts:
            v = [0.0] * EMBEDDING_DIM
            for word in re.findall(r"\w+", text.lower()):
                h = int(hashlib.md5(word.encode()).hexdigest(), 16)  # noqa: S324 - not security-relevant
                v[h % EMBEDDING_DIM] += 1.0
            norm = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / norm for x in v])
        return out


@lru_cache(maxsize=1)
def default_embedder() -> Embedder | None:
    """The E5 model when its files are present, else None (explanations then fall back to the template)."""
    model_dir = Path(settings.data_dir) / MODEL_DIR
    if not (model_dir / "onnx" / "model_quantized.onnx").exists():
        return None
    return E5Embedder(model_dir)
