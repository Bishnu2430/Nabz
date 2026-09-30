"""Retrieve passages for the tests being explained: filtered by test, ranked by meaning (pgvector cosine)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.explain.payload import TestItem
from app.explain.prompt import Passage
from app.knowledge.embed import Embedder
from app.models import KbChunk, KbDocument, LabTest
from app.models.enums import Lang

QUERY = {
    "low": "{test}: what does a low result mean?",
    "high": "{test}: what does a high result mean?",
    "normal": "{test}: what does this test measure and what is a normal result?",
    "unknown": "{test}: what does this test measure?",
}


def trim(text: str, max_words: int) -> str:
    """At most `max_words`, ending at a sentence boundary when there is one."""
    words = text.split()
    if len(words) <= max_words:
        return text
    cut = " ".join(words[:max_words])
    end = max(cut.rfind(". "), cut.rfind(".\n"))
    return cut[: end + 1] if end > len(cut) // 2 else cut + " …"


def retrieve(session: Session, embedder: Embedder, items: list[TestItem], per_test: int = 1,
             max_words: int = 110) -> list[Passage]:
    """The `per_test` most relevant English passages per test, trimmed, labelled P1, P2, … in order.

    One short passage per test keeps a whole report's prompt within a few thousand tokens (Groq's free tier allows
    8,000 a minute) while still grounding what the model says about each test.
    """
    if not items:
        return []
    ids = {code: id_ for code, id_ in session.execute(select(LabTest.code, LabTest.id))}
    queries = [QUERY.get(i.status.replace("critical_", ""), QUERY["unknown"]).format(test=i.test) for i in items]
    vectors = embedder.embed(queries, "query")
    passages: list[Passage] = []
    for item, vector in zip(items, vectors, strict=True):
        rows = session.execute(
            select(KbChunk, KbDocument.title)
            .join(KbDocument, KbDocument.id == KbChunk.document_id)
            .where(KbChunk.test_id == ids.get(item.test_code), KbChunk.language == Lang.EN)
            .order_by(KbChunk.embedding.cosine_distance(vector))
            .limit(per_test)
        ).all()
        for chunk, title in rows:
            passages.append(Passage(f"P{len(passages) + 1}", str(chunk.id), item.test_code, title,
                                    trim(chunk.content, max_words)))
    return passages
