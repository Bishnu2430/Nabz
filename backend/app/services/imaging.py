"""Take the picture and the radiologist's words out of an imaging report, so the app can show the study itself.

A PDF from a radiology centre usually holds one large image (the X-ray or a representative MRI slice) and text
with FINDINGS and IMPRESSION sections. The largest embedded image is kept as a JPEG; the sections are split into
their bullet points. Nothing is interpreted: this is the centre's own text, shown as written.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c

MIN_SIDE = 200  # logos and barcodes are smaller than any study image
TITLE = re.compile(r"^(?:X-?RAY|MRI|CT|USG|ULTRASOUND|ULTRASONOGRAPHY|MAMMOGRAPHY|DEXA|HRCT)\b.*$", re.M)


@dataclass
class Study:
    image: bytes | None = None
    title: str | None = None
    findings: list[str] = field(default_factory=list)
    impression: list[str] = field(default_factory=list)
    credit: str | None = None  # "Image: <author> · <licence>" when the report prints one; shown with the image


def _bullets(block: str) -> list[str]:
    """Bullet points, or sentences when the report has none, rejoined across line breaks."""
    items: list[str] = []
    for part in re.split(r"(?:^|\n)\s*[•\-•]\s*", block):
        text = " ".join(line.strip() for line in part.splitlines() if line.strip())
        if text:
            items.append(text)
    return items


def _sections(text: str) -> tuple[str | None, list[str], list[str]]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    title = m.group(0).strip() if (m := TITLE.search(text)) else None
    findings = re.search(r"\bFINDINGS\b:?\s*\n(.*?)(?=\n\s*IMPRESSION\b)", text, re.S)
    impression = re.search(r"\bIMPRESSION\b:?\s*\n(.*?)(?=\n\s*(?:Dr\.|This report|Page \d)|\Z)", text, re.S)
    return title, _bullets(findings.group(1)) if findings else [], _bullets(impression.group(1)) if impression else []


def extract_study(data: bytes, mime: str) -> Study:
    if mime.startswith("image/"):
        return Study(image=data)
    if mime != "application/pdf":
        return Study()
    study = Study()
    try:
        pdf = pdfium.PdfDocument(data)
    except pdfium.PdfiumError:
        return study
    try:
        best: tuple[int, bytes] | None = None
        texts = []
        for page in pdf:
            texts.append(page.get_textpage().get_text_range())
            for obj in page.get_objects(filter=[pdfium_c.FPDF_PAGEOBJ_IMAGE]):
                try:
                    image = obj.get_bitmap(render=False).to_pil()
                except pdfium.PdfiumError:
                    continue
                w, h = image.size
                if min(w, h) < MIN_SIDE or (best and w * h <= best[0]):
                    continue
                buf = io.BytesIO()
                image.convert("RGB").save(buf, format="JPEG", quality=92)
                best = (w * h, buf.getvalue())
        study.image = best[1] if best else None
        text = "\n".join(texts).replace("\r\n", "\n").replace("\r", "\n")
        study.title, study.findings, study.impression = _sections(text)
        if credit := re.search(r"^Image: .+$", text, re.M):
            study.credit = credit.group(0).strip()
    finally:
        pdf.close()
    return study
