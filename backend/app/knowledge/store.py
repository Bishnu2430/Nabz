"""Load data/knowledge/chunks.jsonl into kb_document and kb_chunk, embedding every chunk. Safe to re-run."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.knowledge.embed import Embedder
from app.models import KbChunk, KbDocument, LabTest
from app.models.enums import Lang


@dataclass(frozen=True)
class LoadResult:
    documents: int
    chunks: int
    skipped_tests: int


def read_chunks(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_knowledge(session: Session, embedder: Embedder, path: Path) -> LoadResult:
    rows = read_chunks(path)
    ids = {code: id_ for code, id_ in session.execute(select(LabTest.code, LabTest.id))}
    by_doc: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_doc[r["url"]].append(r)

    skipped = 0
    chunks = 0
    for url, doc_rows in by_doc.items():
        first = doc_rows[0]
        doc = session.scalar(select(KbDocument).where(KbDocument.url == url))
        if doc is None:
            doc = KbDocument(url=url)
            session.add(doc)
        doc.title = first["title"]
        doc.source_org = first["source_org"]
        doc.license = first["license"]
        doc.language = Lang(first.get("language", "en"))
        doc.retrieved_at = date.fromisoformat(first["retrieved_at"])
        doc.checksum = first["sha256"]
        session.flush()
        session.execute(delete(KbChunk).where(KbChunk.document_id == doc.id))

        wanted = [r for r in doc_rows if r["test_code"] in ids]
        skipped += len(doc_rows) - len(wanted)
        vectors = embedder.embed([f"{r['title']}. {r['section']}\n{r['text']}" for r in wanted], "passage")
        for i, (r, vector) in enumerate(zip(wanted, vectors, strict=True)):
            session.add(KbChunk(document_id=doc.id, test_id=ids[r["test_code"]], chunk_index=i,
                                content=f"{r['section']}\n{r['text']}", language=doc.language, embedding=vector,
                                token_count=len(r["text"].split())))
            chunks += 1
    session.flush()
    return LoadResult(len(by_doc), chunks, skipped)
