"""MedlinePlus Connect → chunked, licence-checked passages (docs/09 §3).

MedlinePlus Connect is NLM's web service that returns MedlinePlus content for a LOINC code. For lab tests it returns
the full "lab test" page (What is it? What is it used for? What do the results mean? …); for other codes, a health
topic summary. NLM-authored MedlinePlus content is in the public domain; pages carrying licensed third-party
content (A.D.A.M.) are rejected. Connect asks for at most 100 requests a minute; this tool sends one a second.

Kept sections: what the test is, what it is used for, what the results mean, anything else to know. Dropped:
why you need it, what happens during it, preparation, risks, references (procedure, not interpretation).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

from app.catalogue import read_catalogue
from app.core.config import settings

CONNECT = "https://connect.medlineplus.gov/service"
LICENSE = "Public domain (US National Library of Medicine, MedlinePlus); no A.D.A.M. content"
SOURCE = "US National Library of Medicine, MedlinePlus"
KEEP = re.compile(r"^(what is (a|an|the)?\b|what is it used for|what do the results mean|is there anything else)", re.I)
MAX_WORDS = 180
# Tests whose LOINC code returns nothing, or a poor match, borrow another test's documents.
BORROW = {"urea": "bun", "urine_pus": "urine_rbc"}


def raw_dir() -> Path:
    return Path(settings.data_dir) / "external" / "medlineplus"


def out_dir() -> Path:
    return Path(settings.data_dir) / "knowledge"


def fetch(directory: Path, codes: dict[str, str]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for test_code, loinc in codes.items():
        path = directory / f"{loinc}.json"
        if path.exists():
            continue
        query = urllib.parse.urlencode({
            "mainSearchCriteria.v.cs": "2.16.840.1.113883.6.1", "mainSearchCriteria.v.c": loinc,
            "knowledgeResponseType": "application/json", "informationRecipient.languageCode.c": "en",
        })
        req = urllib.request.Request(f"{CONNECT}?{query}",  # noqa: S310 - fixed https endpoint
                                     headers={"User-Agent": "Nabz academic prototype"})
        with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 - fixed https URL
            path.write_bytes(r.read())
        print(f"{test_code:18} {loinc:8} {path.stat().st_size:>7,} bytes")
        time.sleep(1.0)


def _text(fragment: str) -> str:
    fragment = re.sub(r"<li[^>]*>", "\n- ", fragment)
    fragment = re.sub(r"</(p|ul|ol|li|h\d)>|<br\s*/?>", "\n", fragment)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    lines = [re.sub(r"\s+", " ", html.unescape(line)).strip() for line in fragment.split("\n")]
    return "\n".join(line for line in lines if line)


def sections(summary_html: str) -> list[tuple[str, str]]:
    """(heading, text) pairs; a page without headings is one "Summary" section."""
    parts = re.split(r"<h2[^>]*>(.*?)</h2>", summary_html, flags=re.S)
    if len(parts) == 1:
        return [("Summary", _text(parts[0]))]
    return [(_text(parts[i]), _text(parts[i + 1])) for i in range(1, len(parts) - 1, 2)]


def chunk(text: str, max_words: int = MAX_WORDS) -> list[str]:
    """Whole paragraphs (and list items) up to ~max_words; a longer paragraph is split at sentences."""
    pieces: list[str] = []
    for para in text.split("\n"):
        words = para.split()
        if len(words) <= max_words:
            pieces.append(para)
            continue
        current: list[str] = []
        for sentence in re.split(r"(?<=[.!?])\s+", para):
            if current and len(" ".join(current + [sentence]).split()) > max_words:
                pieces.append(" ".join(current))
                current = []
            current.append(sentence)
        if current:
            pieces.append(" ".join(current))
    chunks: list[str] = []
    current_chunk: list[str] = []
    for piece in pieces:
        if current_chunk and len(" ".join(current_chunk + [piece]).split()) > max_words:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
        current_chunk.append(piece)
    if current_chunk:
        chunks.append("\n".join(current_chunk))
    return chunks


def build(directory: Path, codes: dict[str, str], out: Path, retrieved: str) -> tuple[list[dict], list[dict]]:
    chunks: list[dict] = []
    manifest: dict[str, dict] = {}
    for test_code in codes:
        path = directory / f"{codes[BORROW.get(test_code, test_code)]}.json"
        if not path.exists():
            continue
        raw = path.read_bytes()
        entries = json.loads(raw).get("feed", {}).get("entry", [])
        lab = [e for e in entries if "/lab-tests/" in e["link"][0]["href"]]
        for e in lab or entries[:1]:  # the lab-test page, else the first health topic
            url = e["link"][0]["href"].split("?")[0]
            summary = e.get("summary", {}).get("_value", "")
            if "A.D.A.M" in summary or "/ency/" in url:
                continue  # licensed third-party content
            title = e["title"]["_value"]
            digest = hashlib.sha256(summary.encode("utf-8")).hexdigest()
            doc = manifest.setdefault(url, {"url": url, "title": title, "license": LICENSE, "retrieved_at": retrieved,
                                            "sha256": digest, "tests": []})
            doc["tests"].append(test_code)
            for heading, text in sections(summary):
                if heading != "Summary" and not KEEP.match(heading):
                    continue
                for piece in chunk(text):
                    chunks.append({"test_code": test_code, "url": url, "title": title, "section": heading,
                                   "text": piece, "source_org": SOURCE, "license": LICENSE, "language": "en",
                                   "retrieved_at": retrieved, "sha256": digest})
    out.mkdir(parents=True, exist_ok=True)
    with (out / "chunks.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    rows = [{**d, "tests": "|".join(d["tests"])} for d in manifest.values()]
    with (out / "manifest.csv").open("w", encoding="utf-8", newline="\n") as f:
        writer = csv.DictWriter(f, fieldnames=["url", "title", "tests", "license", "retrieved_at", "sha256"],
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return chunks, rows


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m tools.knowledge")
    ap.add_argument("command", choices=["fetch", "build"])
    ap.add_argument("--raw", default=str(raw_dir()))
    ap.add_argument("--out", default=str(out_dir()))
    a = ap.parse_args()
    catalogue = read_catalogue(Path(settings.data_dir) / "catalogue")
    codes = {t.code: t.loinc for t in catalogue.tests}
    if a.command == "fetch":
        fetch(Path(a.raw), codes)
        return
    chunks, docs = build(Path(a.raw), codes, Path(a.out), date.today().isoformat())
    covered = {c["test_code"] for c in chunks}
    missing = sorted(set(codes) - covered)
    print(f"{len(chunks)} chunks from {len(docs)} documents, covering {len(covered)} of {len(codes)} tests")
    if missing:
        print("no passages for:", ", ".join(missing), file=sys.stderr)


if __name__ == "__main__":
    main()
