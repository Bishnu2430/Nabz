"""Generate every SVG in docs/diagrams.

    python docs/diagrams/src/build.py            # all diagrams
    python docs/diagrams/src/build.py gantt er   # a subset

Pure standard library; edit the data in this file (or schedule.csv for the
Gantt chart) and re-run to update the figures used by the docs and the report.
"""

from __future__ import annotations

import csv
import sys
from datetime import date, timedelta
from pathlib import Path

from nordsvg import (
    EDGE, FROST_DEEP, GREEN, INK, INK_2, LINE, MONO, MUTED, ORANGE, PAPER, PURPLE, RED,
    SNOW, SNOW_2, TILE, YELLOW, Diagram, icon, text_width,
)

SRC = Path(__file__).resolve().parent
OUT = SRC.parent
VERSION = "v0.1 · 2026-09-26"


# =============================================================================
# 1. System architecture (logical view)
# =============================================================================
def architecture() -> Diagram:
    d = Diagram(1480, 930, "Nabz — system architecture",
                "Logical view. Every box inside the host runs as a Docker container on one Compose network.")

    # Actors
    d.node(100, 300, "Patient / caregiver", "users", "slate", ["phone or laptop", "browser"])
    d.node(100, 520, "Administrator", "admin", "slate", ["catalogue & knowledge", "curation"])

    # Boundaries
    d.group(180, 100, 1020, 580, "Docker host", "slate", "laptop", tint=False,
            sublabel="developer laptop or a single VM")
    d.group(200, 140, 980, 520, "Compose network", "blue", "network", dashed=True, tint=False,
            sublabel="nabz_default")
    d.group(220, 180, 170, 460, "Presentation", "cyan", "browser")
    d.group(410, 180, 170, 460, "API", "blue", "api")
    d.group(600, 180, 200, 460, "Data", "green", "database")
    d.group(820, 180, 170, 460, "Processing", "blue", "gear")
    d.group(1010, 180, 150, 460, "Local AI", "purple", "sparkle", dashed=True)
    d.group(1225, 180, 225, 460, "External APIs", "orange", "cloud", dashed=True)

    # Nodes
    d.node(305, 300, "Web app", "browser", "cyan", ["React + TypeScript", "3D body map · i18n"])
    d.node(305, 520, "3D anatomy", "body", "cyan", ["organ meshes (GLB)", "from Z-Anatomy"])
    d.node(495, 300, "API", "api", "blue", ["FastAPI · REST", "auth · consent", "uploads"])
    d.node(700, 300, "PostgreSQL 17", "database", "green", ["+ pgvector", "records · jobs · vectors"])
    d.node(700, 520, "Uploads volume", "disk", "green", ["report images", "and PDFs"])
    d.node(905, 300, "Worker", "gear", "blue", ["pipeline runner", "OCR · parse · analyse", "explain · narrate"])
    d.node(905, 520, "Models", "scan", "purple", ["PaddleOCR · e5-small", "in-process · CPU"])
    d.node(1085, 300, "Ollama", "sparkle", "purple", ["Qwen3-4B · Q4", "profile: local-llm"])
    d.node(1337, 300, "LLM API", "sparkle", "orange", ["gpt-oss-120b on Groq", "explanations; vision", "model for fallback"])
    d.node(1337, 520, "TTS API", "speaker", "orange", ["Indian-language", "voices (optional)"])

    # Flows
    c = INK_2
    d.arrow([(126, 300), (279, 300)], c)
    d.step(200, 300, 1)
    d.arrow([(126, 520), (250, 520), (250, 314), (279, 314)], c, dash="5 4")
    d.arrow([(331, 300), (469, 300)], c, tail="arrow")
    d.step(400, 300, 2)
    d.arrow([(521, 300), (674, 300)], c)
    d.step(590, 300, 3)
    d.arrow([(521, 314), (590, 314), (590, 520), (674, 520)], c)
    d.arrow([(879, 300), (726, 300)], c, tail="arrow")
    d.step(810, 300, 4)
    d.arrow([(879, 314), (810, 314), (810, 520), (726, 520)], c)
    d.arrow([(905, 394), (905, 494)], c, dash="5 4")
    d.arrow([(931, 300), (1059, 300)], PURPLE, dash="5 4", tail="arrow")
    d.step(1000, 300, 5, TILE["purple"])
    d.arrow([(905, 274), (905, 222), (1337, 222), (1337, 274)], TILE["orange"], tail="arrow")
    d.step(1192, 222, 6, TILE["orange"])
    d.arrow([(931, 316), (1000, 316), (1000, 440), (1337, 440), (1337, 494)], TILE["orange"])
    d.step(1192, 440, 7, TILE["orange"])
    d.arrow([(305, 380), (305, 494)], c, dash="5 4")
    d.step(305, 437, 8)

    # Steps panel
    steps = [
        "Patient or caregiver opens the web app on a phone or laptop.",
        "The web app calls the REST API: upload, review values, fetch results.",
        "API saves the file to the uploads volume and writes report + job rows.",
        "Worker claims the job (FOR UPDATE SKIP LOCKED), reads the file, runs OCR.",
        "Ambiguous rows are structured by the local 3–4B model (optional profile).",
        "After the user confirms values: de-identified values + retrieved passages → LLM API.",
        "The explanation passes the safety validator; narration comes from the TTS API.",
        "The web app renders the 3D body map, trends and explanation.",
    ]
    d.rect(180, 705, 820, 190, fill=SNOW, stroke="none", rx=6)
    d.text(200, 730, "Request flow", 12.5, 650, INK)
    for i, s in enumerate(steps):
        col, row = divmod(i, 4)
        x, y = 210 + col * 400, 758 + row * 36
        d.step(x, y - 4, i + 1, TILE["orange"] if i in (5, 6) else (TILE["purple"] if i == 4 else INK))
        d.lines(x + 20, y - 4 - 5, _wrap(s, 52), 11, 400, INK_2, leading=1.3)

    d.card(1020, 705, 430, 190, "Data minimisation", [
        "Report images, names and IDs never leave the host",
        "by default. Explanations receive only de-identified",
        "values: test, value, unit, range, age band and sex.",
        "The vision fallback sends an image only after",
        "explicit, per-report consent.",
    ], role="green", glyph="lock")

    d.legend(1030, 150 - 60, [("line", INK_2, "request / data"), ("dash", INK_2, "mount / optional"),
                              ("line", TILE["orange"], "internet egress")])
    d.footer(f"Nabz · docs/diagrams/architecture.svg · {VERSION}")
    return d


# =============================================================================
# 2. Deployment topology (Docker Compose)
# =============================================================================
def deployment() -> Diagram:
    d = Diagram(1480, 1050, "Nabz — deployment topology",
                "Physical view of the development and demo environment: one Compose project on one machine.")

    d.group(30, 90, 1180, 730, "Developer laptop", "slate", "laptop", tint=False,
            sublabel="Windows 11 · Intel i5-1235U · 16 GB RAM · integrated GPU (no CUDA)")
    d.group(50, 130, 1140, 670, "Docker Desktop", "slate", "cube", dashed=True, tint=False,
            sublabel="WSL 2 VM · memory limit 10 GB (.wslconfig)")
    d.group(70, 170, 1100, 460, "Compose project  nabz", "blue", "network", dashed=True,
            sublabel="bridge network nabz_default · service DNS: db, api, worker, web, ollama")

    cw, ch = 250, 180

    def container(x: float, y: float, name: str, glyph: str, role: str,
                  rows: list[tuple[str, str]], tag: str) -> None:
        d.card(x, y, cw, ch, name, None, role=role, glyph=glyph)
        for i, (k, v) in enumerate(rows):
            ry = y + 64 + i * 21
            d.text(x + 16, ry, k, 10.5, 500, MUTED, family=MONO)
            d.text(x + 76, ry, v, 11, 400, INK_2)
        w = text_width(tag, 10, 600) + 14
        d.rect(x + cw - w - 10, y + 15, w, 20, fill=EDGE[role], stroke="none", rx=10, opacity=0.25)
        d.text(x + cw - 10 - w / 2, y + 29, tag, 10, 600, TILE[role], "middle")

    container(90, 215, "web", "browser", "cyan", [
        ("image", "node:22-alpine"), ("cmd", "vite dev server"), ("port", "127.0.0.1:5173"),
        ("mounts", "./frontend (hot reload)"), ("build", "static files in production")], "Sprint 3")
    container(360, 215, "api", "api", "blue", [
        ("image", "./backend · python:3.12 + uv"), ("cmd", "uvicorn app.main:app"), ("port", "127.0.0.1:8000"),
        ("mounts", "uploads, ./backend/app"), ("health", "GET /health/ready")], "running")
    container(630, 215, "worker", "gear", "blue", [
        ("image", "same image as api"), ("cmd", "python -m app.worker"), ("port", "none (internal only)"),
        ("mounts", "uploads, model-cache"), ("queue", "Postgres SKIP LOCKED")], "Sprint 2")
    container(900, 215, "ollama", "sparkle", "purple", [
        ("image", "ollama/ollama"), ("model", "qwen3:4b · Q4 · ~2.5 GB"), ("port", "127.0.0.1:11434"),
        ("mounts", "ollama"), ("profile", "local-llm (opt-in)")], "optional")
    container(360, 430, "db", "database", "green", [
        ("image", "pgvector/pgvector:pg17"), ("ext", "vector · pg_trgm · pgcrypto"), ("port", "127.0.0.1:5433 → 5432"),
        ("mounts", "pgdata, infra/db/init"), ("health", "pg_isready")], "running")

    # relationships
    d.arrow([(340, 305), (360, 305)], INK_2)
    d.pill(350, 287, "REST")
    d.arrow([(485, 395), (485, 430)], INK_2)
    d.arrow([(755, 395), (755, 412), (590, 412), (590, 430)], INK_2)
    d.pill(672, 412, "SQL + job queue")

    # volumes
    vy = 520
    for x, name, sub in [(700, "pgdata", "← db"), (820, "uploads", "← api, worker"),
                         (940, "model-cache", "← worker"), (1060, "ollama", "← ollama")]:
        d.node(x, vy, name, "disk", "green", sub, size=44)
    d.text(640, 470, "Named volumes", 11.5, 650, INK_2)

    # port bindings
    d.text(90, 668, "Published ports (bound to 127.0.0.1 only — not reachable from the LAN)", 11.5, 650, INK_2)
    for i, (p, s) in enumerate([(":5173", "web app"), (":8000", "API + OpenAPI docs"),
                                (":5433", "Postgres for DB tools"), (":11434", "Ollama (optional)")]):
        x = 90 + i * 270
        d.rect(x, 684, 250, 34, fill=SNOW, stroke=LINE, rx=17)
        d.text(x + 18, 706, p, 12, 700, INK, family=MONO)
        d.text(x + 80, 706, s, 11.5, 400, INK_2)
    d.node(130, 762, "", "browser", "slate", None, size=30)
    d.text(156, 767, "Browser on the same laptop", 11.5, 600, INK)
    d.arrow([(130, 747), (130, 721)], INK_2)

    # egress
    d.group(1240, 170, 215, 460, "Egress · HTTPS 443", "orange", "globe", dashed=True)
    d.node(1347, 270, "LLM API", "sparkle", "orange", ["api.groq.com"])
    d.node(1347, 400, "TTS provider", "speaker", "orange", ["optional"])
    d.node(1347, 530, "Model registries", "cloud", "orange", ["first-run downloads"])
    d.arrow([(880, 380), (890, 380), (890, 412), (1305, 412), (1305, 270), (1321, 270)], TILE["orange"])
    d.arrow([(1305, 412), (1305, 400), (1321, 400)], TILE["orange"])
    d.arrow([(1150, 330), (1285, 330), (1285, 530), (1321, 530)], TILE["orange"], dash="5 4")
    d.pill(1080, 412, "worker → external APIs", TILE["orange"])

    # resource budget
    d.rect(30, 845, 1425, 170, fill=SNOW, stroke="none", rx=6)
    d.text(50, 871, "Memory budget (estimated, steady state)", 12.5, 650, INK)
    cols = [50, 230, 520, 650, 800]
    head = ["Service", "Main consumers", "RAM", "CPU", "Notes"]
    for x, h in zip(cols, head):
        d.text(x, 897, h, 11, 700, MUTED)
    rows = [
        ("db", "shared buffers, pgvector index", "0.3–0.5 GB", "low", "tune shared_buffers=256MB"),
        ("api", "FastAPI workers", "0.2–0.3 GB", "low", "2 uvicorn workers in demo mode"),
        ("worker", "PaddleOCR + e5-small + pandas", "1.2–1.8 GB", "burst 100%", "one job at a time on a 10-core laptop CPU"),
        ("ollama", "Qwen3-4B Q4_K_M weights + KV cache", "3.0–3.5 GB", "burst 100%", "only with --profile local-llm"),
        ("web", "Vite dev server", "0.3–0.5 GB", "low", "production build is static files"),
    ]
    for i, r in enumerate(rows):
        y = 919 + i * 18
        for x, v in zip(cols, r):
            d.text(x, y, v, 11, 600 if x == 50 else 400, INK if x == 50 else INK_2,
                   family=MONO if x == 50 else None)
    d.text(1100, 919, "Total ≈ 5–6.5 GB", 13, 700, INK)
    d.lines(1100, 941, ["fits inside a 10 GB WSL 2 limit,", "leaving ~6 GB for Windows,", "the browser and the IDE."],
            11, 400, INK_2)
    d.footer(f"Nabz · docs/diagrams/deployment.svg · {VERSION}")
    return d


# =============================================================================
# 3. Report processing pipeline
# =============================================================================
KIND = {  # stage kind → (tile role, legend label)
    "rule": ("blue", "deterministic code"),
    "ml": ("green", "ML / data science"),
    "genai": ("purple", "generative AI"),
    "human": ("orange", "human in the loop"),
}


def pipeline() -> Diagram:
    d = Diagram(1480, 1000, "Nabz — report processing pipeline",
                "From a phone photo to an explained, verified, 3D-rendered report. Every stage writes its output to Postgres.")
    rows = [
        ("A", "Ingest & extract", "automatic · worker", [
            ("Upload & validate", "rule", "type, size, page count;", "blur / skew / glare score", "FastAPI · OpenCV"),
            ("Pre-process", "rule", "deskew, denoise,", "contrast, crop to page", "OpenCV"),
            ("OCR", "ml", "text lines + boxes", "with confidences", "PaddleOCR PP-OCRv5"),
            ("Parse rows", "rule", "table layout → rows of", "name · value · unit · range", "layout rules"),
            ("Map to catalogue", "ml", "aliases → LOINC codes;", "ambiguous rows → small LLM", "pg_trgm · Qwen3-4B"),
            ("Normalise & score", "ml", "units, plausibility, a", "calibrated confidence", "scikit-learn"),
        ]),
        ("B", "Verify & analyse", "user confirms · worker computes", [
            ("Human review", "human", "values beside the image;", "low-confidence rows first", "web app"),
            ("Classify", "rule", "low / normal / high vs", "report or catalogue range", "Python rules"),
            ("Critical values", "rule", "fixed thresholds →", "fixed urgent message", "reviewed rule table"),
            ("Change & trend", "ml", "reference change value,", "Theil–Sen slope, projection", "SciPy · statsmodels"),
            ("Percentile", "ml", "position vs population", "by age band and sex", "NHANES tables"),
        ]),
        ("C", "Explain & present", "grounded generation · safety first", [
            ("Retrieve", "ml", "top-k passages per test", "from the knowledge base", "pgvector · e5-small"),
            ("Explain", "genai", "plain-language summary +", "questions for the doctor", "gpt-oss-120b · Groq"),
            ("Safety check", "rule", "no diagnosis, no dosing,", "numbers match the source", "validator + judge"),
            ("Narrate", "genai", "voice in English,", "Hindi or Odia", "TTS API (optional)"),
            ("Render", "rule", "organ status, timeline,", "report ↔ organ links", "React Three Fiber"),
        ]),
    ]
    cw, chh, gap = 208, 128, 26
    x0, y0, row_gap = 50, 130, 262
    n = 0
    for r, (letter, title, sub, stages) in enumerate(rows):
        y = y0 + r * row_gap
        d.rect(x0 - 20, y - 22, 1420, row_gap - 40, fill=SNOW, stroke="none", rx=8)
        d.text(x0, y, f"{letter} · {title}", 14, 700, INK)
        d.text(x0 + text_width(f"{letter} · {title}", 14, 700) + 14, y, sub, 11.5, 400, MUTED)
        for i, (name, kind, l1, l2, tech) in enumerate(stages):
            n += 1
            cx = x0 + i * (cw + gap)
            cy = y + 22
            role = KIND[kind][0]
            d.rect(cx, cy, cw, chh, fill=PAPER, stroke=LINE, rx=8)
            d.rect(cx, cy, cw, 5, fill=TILE[role], stroke="none", rx=2)
            d.step(cx + 24, cy + 30, n, TILE[role])
            d.text(cx + 44, cy + 35, name, 13, 650, INK)
            d.lines(cx + 16, cy + 62, [l1, l2], 11, 400, INK_2, leading=1.4)
            d.rect(cx + 12, cy + chh - 32, cw - 24, 22, fill=SNOW, stroke="none", rx=4)
            d.text(cx + cw / 2, cy + chh - 17, tech, 10.5, 500, INK_2, "middle", family=MONO)
            if i < len(stages) - 1:
                d.arrow([(cx + cw + 2, cy + chh / 2), (cx + cw + gap - 2, cy + chh / 2)], INK_2)
        # connector to next row
        if r < len(rows) - 1:
            last_x = x0 + (len(stages) - 1) * (cw + gap) + cw / 2
            ny = y + row_gap + 22
            d.arrow([(last_x, y + 22 + chh + 2), (last_x, y + 22 + chh + 30), (x0 + cw / 2, y + 22 + chh + 30),
                     (x0 + cw / 2, ny - 2)], INK_2)

    # gates / notes
    gate_y = y0 + 22 + chh + 30
    d.pill(760, gate_y, "rows with confidence < τ are highlighted for review", TILE["orange"])
    d.pill(760, gate_y + row_gap, "only de-identified values continue to external services", TILE["green"])
    d.card(1222, y0 + row_gap + 22, 228, chh, "Why a human step?", [
        "OCR and mapping errors are",
        "caught before anything is",
        "interpreted: nothing is explained",
        "until the numbers are confirmed.",
    ], role="orange", glyph="user", row_size=10.8)
    d.card(1222, y0 + 2 * row_gap + 22, 228, chh, "Grounding", [
        "Text is generated only from",
        "confirmed values and retrieved",
        "passages; every number is",
        "re-checked against the source.",
    ], role="purple", glyph="shield", row_size=10.8)

    # artefacts strip
    ay = 870
    d.text(50, ay, "Artefacts written", 12.5, 650, INK)
    arts = [("report_file", "1"), ("report_page (OCR JSON)", "3"), ("observation · draft", "4–6"),
            ("observation · verified", "7"), ("trend_insight", "10–11"), ("explanation + citations", "12–14"),
            ("audio (volume)", "15")]
    x = 50
    for name, st in arts:
        w = text_width(name, 11, mono=True) + text_width(st, 10) + 44
        d.rect(x, ay + 14, w, 28, fill=PAPER, stroke=LINE, rx=14)
        d.text(x + 14, ay + 32, name, 11, 500, INK, family=MONO)
        d.text(x + w - 14, ay + 32, st, 10, 600, MUTED, "end")
        x += w + 10

    d.legend(50, 950, [("box", TILE[r], lbl) for r, lbl in KIND.values()])
    d.footer(f"Nabz · docs/diagrams/pipeline.svg · {VERSION}")
    return d


# =============================================================================
# UML helpers
# =============================================================================
def actor(d: Diagram, cx: float, cy: float, label: str, sub: str | None = None) -> None:
    """Stick-figure actor; (cx, cy) is the hip."""
    s = f'stroke="{INK}" stroke-width="1.6" fill="none" stroke-linecap="round"'
    d.raw(f'<circle cx="{cx}" cy="{cy - 40}" r="10" fill="{PAPER}" stroke="{INK}" stroke-width="1.6"/>'
          f'<path d="M{cx},{cy - 30} V{cy} M{cx - 17},{cy - 20} H{cx + 17} '
          f'M{cx},{cy} L{cx - 13},{cy + 24} M{cx},{cy} L{cx + 13},{cy + 24}" {s}/>')
    d.text(cx, cy + 44, label, 12.5, 650, INK, "middle")
    if sub:
        d.text(cx, cy + 60, sub, 10.8, 400, MUTED, "middle")


def system_actor(d: Diagram, cx: float, cy: float, label: str, sub: str, glyph: str, role: str) -> None:
    d.rect(cx - 95, cy - 34, 190, 68, fill=PAPER, stroke=EDGE[role], sw=1.4, rx=6)
    d.rect(cx - 83, cy - 20, 40, 40, fill=TILE[role], stroke="none", rx=7)
    d.raw(icon(glyph, cx - 75, cy - 12, 24))
    d.text(cx - 32, cy - 10, "«system»", 10, 500, MUTED)
    d.text(cx - 32, cy + 6, label, 12.5, 650, INK)
    d.text(cx - 32, cy + 21, sub, 10.5, 400, MUTED)


def usecase(d: Diagram, cx: float, cy: float, uc: str, name: str, role: str = "blue",
            rx: float = 118, ry: float = 27) -> None:
    d.raw(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{PAPER}" stroke="{EDGE[role]}" stroke-width="1.5"/>')
    d.text(cx, cy - 4, uc, 9.8, 600, TILE[role], "middle")
    d.text(cx, cy + 11, name, 12, 600, INK, "middle")


# =============================================================================
# 4. Use-case diagram
# =============================================================================
def use_case() -> Diagram:
    d = Diagram(1480, 1010, "Nabz — use-case model",
                "Who uses Nabz and for what. Solid lines are associations; dashed arrows are «include» / «extend».")
    d.rect(340, 100, 790, 870, fill=SNOW, stroke=INK_2, sw=1.4, rx=10, opacity=0.5)
    d.text(362, 126, "Nabz", 14, 700, INK)
    d.text(408, 126, "system boundary", 11, 400, MUTED)

    ax, bx = 560, 905
    col_a = [
        ("UC-01", "Sign up / sign in", 175), ("UC-02", "Manage family profiles", 245),
        ("UC-04", "Upload a lab report", 315), ("UC-05", "Review & correct values", 385),
        ("UC-06", "Explore the 3D body map", 455), ("UC-07", "View trends over time", 525),
        ("UC-08", "Read the explanation", 595), ("UC-11", "Share a summary with a doctor", 665),
        ("UC-12", "Export or delete my data", 735),
    ]
    for uc, name, y in col_a:
        usecase(d, ax, y, uc, name)
    actor(d, 170, 440, "Patient / caregiver", "primary actor")
    for _, _, y in col_a:
        d.line(190, 422, ax - 118, y, INK_2, 1.2)

    # included / extending use cases
    usecase(d, bx, 315, "UC-03", "Give / withdraw consent", "green")
    usecase(d, bx, 385, "UC-13", "Critical-value alert", "red")
    usecase(d, bx, 525, "UC-10", "Questions for the doctor", "blue")
    usecase(d, bx, 595, "UC-18", "Generate grounded explanation", "purple")
    usecase(d, bx, 665, "UC-09", "Listen to the explanation", "purple")
    usecase(d, bx, 810, "UC-17", "View a shared summary", "cyan")

    def dep(p1, p2, kind, lx=None, ly=None):
        d.arrow([p1, p2], INK_2, sw=1.2, dash="5 4", head="open")
        mx = lx if lx is not None else (p1[0] + p2[0]) / 2
        my = ly if ly is not None else (p1[1] + p2[1]) / 2
        d.pill(mx, my, kind, MUTED, 10)

    dep((ax + 118, 315), (bx - 118, 315), "«include»")
    dep((bx - 118, 385), (ax + 118, 385), "«extend»")
    dep((ax + 104, 582), (bx - 110, 535), "«include»", 732, 560)
    dep((ax + 118, 595), (bx - 118, 595), "«include»", 732, 606)
    dep((bx - 110, 655), (ax + 104, 607), "«extend»", 732, 640)
    d.text(bx, 422, "condition: a value crosses a critical limit", 10, 400, MUTED, "middle", italic=True)

    # doctor
    actor(d, 170, 820, "Doctor", "secondary actor")
    d.line(190, 802, bx - 118, 810, INK_2, 1.2)
    d.text(bx, 852, "via an expiring share link — no account needed", 10.5, 400, MUTED, "middle", italic=True)

    # administrator
    usecase(d, bx, 175, "UC-14", "Curate the test catalogue", "orange")
    usecase(d, bx, 245, "UC-15", "Manage the knowledge base", "orange")
    usecase(d, bx, 455, "UC-16", "Review audit & safety reports", "orange")
    actor(d, 1310, 250, "Administrator", "clinical content owner")
    for y in (175, 245, 455):
        d.line(1290, 235, bx + 118, y, INK_2, 1.2)

    # external systems
    system_actor(d, 1310, 595, "LLM service", "explanations", "sparkle", "purple")
    system_actor(d, 1310, 700, "TTS service", "narration", "speaker", "purple")
    d.line(1215, 595, bx + 118, 595, INK_2, 1.2)
    d.line(1215, 700, bx + 118, 665, INK_2, 1.2)

    d.card(380, 870, 400, 80, "Out of scope (by design)", [
        "Diagnosis · prescribing or dosing advice ·",
        "emergency triage · replacing a clinician",
    ], role="red", glyph="alert")
    d.footer(f"Nabz · docs/diagrams/use-case.svg · {VERSION}")
    return d


# =============================================================================
# 5. Activity diagram (swimlanes)
# =============================================================================
def activity() -> Diagram:
    d = Diagram(1480, 1720, "Nabz — activity diagram: from upload to explanation",
                "UML activity diagram with one swimlane per participant. Diamonds mark decisions and merges; dashed actions are optional.")
    lanes = [("User", 40, 280, "slate"), ("Web app", 280, 540, "cyan"), ("API", 540, 800, "blue"),
             ("Worker", 800, 1180, "blue"), ("AI services", 1180, 1440, "purple")]
    top, bottom = 96, 1680
    for i, (name, x1, x2, role) in enumerate(lanes):
        d.rect(x1, top, x2 - x1, bottom - top, fill=SNOW if i % 2 == 0 else PAPER, stroke=LINE, rx=0)
        d.rect(x1, top, x2 - x1, 36, fill=TILE[role], stroke="none", rx=0)
        d.text((x1 + x2) / 2, top + 23, name, 13, 700, PAPER, "middle")
    cx = {"User": 160, "Web": 410, "API": 670, "Worker": 990, "AI": 1310}

    nodes: dict[str, tuple[float, float, float, float]] = {}

    def act(key, lane, y, rows, dashed=False, role="blue"):
        w, h = 220, 22 + 15 * len(rows)
        x = cx[lane]
        d.rect(x - w / 2, y - h / 2, w, h, fill=PAPER, stroke=EDGE[role], sw=1.5, rx=14,
               dash="5 4" if dashed else None)
        d.lines(x, y - h / 2 + 26 - (3 if len(rows) == 1 else 4) + (0 if len(rows) > 1 else 3), rows,
                11.5, 500, INK, "middle", 1.3)
        nodes[key] = (x, y, w / 2, h / 2)

    def dec(key, lane, y, label=None, side="right"):
        x = cx[lane]
        d.raw(f'<path d="M{x},{y - 20} L{x + 20},{y} L{x},{y + 20} L{x - 20},{y} z" fill="{PAPER}" '
              f'stroke="{INK_2}" stroke-width="1.5"/>')
        if label:
            if side == "right":
                d.text(x + 28, y - 26, label, 11, 500, INK_2)
            else:
                d.text(x - 28, y - 26, label, 11, 500, INK_2, "end")
        nodes[key] = (x, y, 20, 20)

    def flow(a, b, label=None, via=None):
        ax_, ay, _, ah = nodes[a]
        bx_, by, bw, bh = nodes[b]
        if via:
            pts = via
        elif abs(ax_ - bx_) < 1:
            pts = [(ax_, ay + ah), (bx_, by - bh)]
        else:
            ex = bx_ - bw if bx_ > ax_ else bx_ + bw
            pts = [(ax_, ay + ah), (ax_, by), (ex, by)]
        d.arrow(pts, INK_2, sw=1.3)
        if label:
            lx, ly = pts[0][0], pts[0][1] + 16
            d.text(lx + 8, ly, label, 10.5, 600, MUTED)

    # start
    d.circle(cx["User"], 165, 11, INK)
    nodes["start"] = (cx["User"], 165, 11, 11)
    act("a1", "User", 230, ["Photograph or choose", "the report file"], role="slate")
    act("a2", "Web", 310, ["Check type, size and", "image quality"], role="cyan")
    dec("d1", "Web", 390, "quality good enough?")
    act("a2b", "User", 390, ["Retake the photo"], role="slate")
    act("a3", "API", 470, ["Check consent · store file", "create report + job"])
    act("a4", "Worker", 550, ["Claim job · pre-process", "run OCR"])
    act("a5", "Worker", 630, ["Parse rows · map to catalogue", "normalise · score confidence"])
    dec("d2", "Worker", 710, "any row below τ?")
    act("a6", "AI", 710, ["Local 3–4B model", "structures those rows"], role="purple")
    dec("m1", "Worker", 790)
    act("a7", "Web", 870, ["Show values beside the image", "low-confidence rows first"], role="cyan")
    act("a8", "User", 950, ["Correct or confirm", "each value"], role="slate")
    act("a9", "Worker", 1030, ["Classify vs ranges · critical rules", "change · trend · percentile"])
    dec("d3", "Worker", 1110, "critical value?")
    act("a10", "Web", 1110, ["Show the fixed", "“see a doctor today” alert"], role="red")
    dec("m2", "Worker", 1190)
    act("a11", "AI", 1270, ["Retrieve passages · write the", "explanation (EN / HI / OR)"], role="purple")
    act("a12", "Worker", 1350, ["Safety validation; on failure", "use the safe template"])
    act("a13", "AI", 1430, ["Synthesise narration", "(if voice is on)"], dashed=True, role="purple")
    act("a14", "Web", 1510, ["Render body map, trends,", "explanation, questions"], role="cyan")
    act("a15", "User", 1590, ["Explore · listen · share", "or export"], role="slate")
    x = cx["User"]
    d.circle(x, 1652, 12, PAPER, INK, 1.6)
    d.circle(x, 1652, 7, INK)
    nodes["end"] = (x, 1652, 12, 12)

    flow("start", "a1")
    flow("a1", "a2")
    flow("a2", "d1")
    d1x, d1y = nodes["d1"][:2]
    d.arrow([(d1x - 20, d1y), (cx["User"] + 110, d1y)], INK_2, sw=1.3)
    d.text(d1x - 30, d1y - 6, "[no]", 10.5, 600, MUTED, "end")
    d.arrow([(cx["User"] - 110, 390), (45, 390), (45, 230), (cx["User"] - 110, 230)], INK_2, sw=1.3)
    flow("d1", "a3", "[yes]")
    flow("a3", "a4")
    flow("a4", "a5")
    flow("a5", "d2")
    d.arrow([(cx["Worker"] + 20, 710), (cx["AI"] - 110, 710)], INK_2, sw=1.3)
    d.text(cx["Worker"] + 30, 704, "[yes]", 10.5, 600, MUTED)
    d.arrow([(cx["AI"], 710 + 26), (cx["AI"], 790), (cx["Worker"] + 20, 790)], INK_2, sw=1.3)
    flow("d2", "m1", "[no]")
    flow("m1", "a7")
    flow("a7", "a8")
    flow("a8", "a9")
    flow("a9", "d3")
    d.arrow([(cx["Worker"] - 20, 1110), (cx["Web"] + 110, 1110)], INK_2, sw=1.3)
    d.text(cx["Worker"] - 30, 1104, "[yes]", 10.5, 600, MUTED, "end")
    d.arrow([(cx["Web"], 1110 + 26), (cx["Web"], 1190), (cx["Worker"] - 20, 1190)], INK_2, sw=1.3)
    flow("d3", "m2", "[no]")
    flow("m2", "a11")
    flow("a11", "a12")
    flow("a12", "a13")
    flow("a13", "a14")
    flow("a14", "a15")
    flow("a15", "end")
    d.footer(f"Nabz · docs/diagrams/activity.svg · {VERSION}")
    return d


# =============================================================================
# 6. Sequence diagram
# =============================================================================
def sequence() -> Diagram:
    parts = [("User", "user", "slate"), ("Web app", "browser", "cyan"), ("API", "api", "blue"),
             ("PostgreSQL", "database", "green"), ("Worker", "gear", "blue"), ("Local LLM", "sparkle", "purple"),
             ("LLM API", "cloud", "orange"), ("TTS API", "speaker", "orange")]
    xs = [95 + i * 184 for i in range(len(parts))]
    X = {p[0]: x for p, x in zip(parts, xs)}
    msgs = [
        ("phase", "1 · Upload and extraction"),
        ("User", "Web app", "choose photo / PDF"),
        ("Web app", "Web app", "quality check"),
        ("Web app", "API", "POST /v1/profiles/{id}/reports"),
        ("API", "PostgreSQL", "INSERT report, file, job (queued)"),
        ("API", "Web app", "202 Accepted {report_id}", "reply"),
        ("Worker", "PostgreSQL", "claim job · FOR UPDATE SKIP LOCKED"),
        ("Worker", "Worker", "pre-process · OCR"),
        ("Worker", "Worker", "parse · map · normalise"),
        ("frame+", "alt", "[row confidence < τ]", "Worker", "Local LLM"),
        ("Worker", "Local LLM", "structure rows (JSON schema)"),
        ("Local LLM", "Worker", "rows JSON", "reply"),
        ("frame-",),
        ("Worker", "PostgreSQL", "INSERT observations · needs_review"),
        ("Web app", "API", "GET /v1/reports/{id}  (SSE)"),
        ("API", "Web app", "status + draft values", "reply"),
        ("phase", "2 · Review, analysis and explanation"),
        ("User", "Web app", "correct / confirm values"),
        ("Web app", "API", "POST /v1/reports/{id}/confirm"),
        ("API", "PostgreSQL", "UPDATE verified · enqueue analyse"),
        ("Worker", "PostgreSQL", "load profile history"),
        ("Worker", "Worker", "ranges · critical · RCV · trend"),
        ("Worker", "PostgreSQL", "kNN search kb_chunk (pgvector)"),
        ("Worker", "LLM API", "de-identified values + passages"),
        ("LLM API", "Worker", "structured explanation", "reply"),
        ("Worker", "Worker", "safety validation"),
        ("frame+", "opt", "[voice narration on]", "Worker", "TTS API"),
        ("Worker", "TTS API", "text + language"),
        ("TTS API", "Worker", "audio", "reply"),
        ("frame-",),
        ("Worker", "PostgreSQL", "INSERT explanation · explained"),
        ("Web app", "API", "GET /v1/reports/{id}/insights"),
        ("API", "Web app", "organs · trends · text · audio", "reply"),
        ("Web app", "User", "3D body map + explanation", "reply"),
    ]
    step = 38
    height = 170 + sum({"frame-": 14, "frame+": 30}.get(m[0], step) for m in msgs) + 90
    d = Diagram(1480, int(height), "Nabz — sequence diagram: upload to explanation",
                "Synchronous calls are solid, replies dashed. The worker and API never call each other; they meet in Postgres.")
    top = 96
    for (name, glyph, role), x in zip(parts, xs):
        d.rect(x - 78, top, 156, 44, fill=PAPER, stroke=EDGE[role], sw=1.5, rx=6)
        d.rect(x - 70, top + 8, 28, 28, fill=TILE[role], stroke="none", rx=5)
        d.raw(icon(glyph, x - 65, top + 13, 18))
        d.text(x - 34, top + 27, name, 12.5, 650, INK)
        d.line(x, top + 44, x, height - 50, "#B8C0CE", 1.2, "4 4")
    y = top + 44 + 30
    n = 0
    frames: list[tuple[str, str, float, float, float]] = []
    for m in msgs:
        if m[0] == "phase":
            d.rect(30, y - 16, 1420, 26, fill=SNOW_2, stroke="none", rx=4)
            d.text(44, y + 2, m[1], 12, 700, INK)
            y += step
            continue
        if m[0] == "frame+":
            _, kind, cond, p1, p2 = m
            frames.append((kind, cond, X[p1] - 60, min(X[p2] + 70, 1460), y - 18))
            y += 30
            continue
        if m[0] == "frame-":
            kind, cond, x1, x2, fy = frames.pop()
            d.rect(x1, fy, x2 - x1, y - fy - 4, fill="none", stroke=INK_2, sw=1.1, rx=2)
            w = text_width(kind, 11, 700) + 18
            d.raw(f'<path d="M{x1},{fy} h{w} v12 l-6,6 h-{w - 6} z" fill="{SNOW_2}" stroke="{INK_2}" stroke-width="1.1"/>')
            d.text(x1 + 8, fy + 13, kind, 11, 700, INK)
            d.text(x1 + w + 8, fy + 13, cond, 11, 500, INK_2)
            y += 14
            continue
        src, dst, label = m[0], m[1], m[2]
        reply = len(m) > 3
        n += 1
        x1, x2 = X[src], X[dst]
        color = TILE["orange"] if "LLM API" in (src, dst) or "TTS API" in (src, dst) else INK_2
        if src == dst:
            d.arrow([(x1, y - 6), (x1 + 36, y - 6), (x1 + 36, y + 10), (x1 + 3, y + 10)], color, sw=1.3)
            d.text(x1 + 44, y + 6, label, 11, 400, INK)
            d.circle(x1 - 14, y + 2, 8, SNOW_2)
            d.text(x1 - 14, y + 5.5, str(n), 9, 700, INK_2, "middle")
        else:
            d.arrow([(x1, y), (x2 + (-4 if x2 > x1 else 4), y)], color, sw=1.3,
                    dash="6 4" if reply else None, head="open" if reply else "arrow")
            left = min(x1, x2)
            d.circle(left + 14, y - 11, 8, SNOW_2)
            d.text(left + 14, y - 7.5, str(n), 9, 700, INK_2, "middle")
            d.text(left + 28, y - 7, label, 11, 400, INK)
        y += step
    d.footer(f"Nabz · docs/diagrams/sequence.svg · {VERSION}")
    return d


# =============================================================================
# 7. State machine — report lifecycle
# =============================================================================
def state_machine() -> Diagram:
    d = Diagram(1480, 800, "Nabz — report lifecycle (state machine)",
                "Values of report.status. Every transition is written by exactly one component and recorded in audit_log.")
    S: dict[str, tuple[float, float]] = {}

    def st(key, x, y, name, sub=None, role="blue", w=170, h=56):
        d.rect(x - w / 2, y - h / 2, w, h, fill=PAPER, stroke=EDGE[role], sw=1.6, rx=16)
        d.text(x, y + (0 if sub else 5), name, 13, 650, INK, "middle")
        if sub:
            d.text(x, y + 16, sub, 10.5, 400, MUTED, "middle", family=MONO)
        S[key] = (x, y)

    def tr(pts, label=None, at=None, color=INK_2):
        d.arrow(pts, color, sw=1.35)
        if label:
            d.pill(*(at or ((pts[0][0] + pts[-1][0]) / 2, (pts[0][1] + pts[-1][1]) / 2)), label, INK_2, 10.3)

    d.circle(70, 250, 11, INK)
    st("up", 190, 250, "Uploaded", "uploaded", "slate")
    st("q", 420, 250, "Queued", "queued")
    # composite
    d.rect(540, 160, 520, 180, fill=SNOW, stroke=FROST_DEEP, sw=1.5, rx=18)
    d.text(560, 184, "Processing", 13, 700, INK)
    d.text(650, 184, "processing", 10.5, 400, MUTED, family=MONO)
    d.circle(575, 260, 8, INK)
    st("pp", 660, 260, "Pre-process", None, "blue", 120, 44)
    st("ocr", 800, 260, "OCR", None, "blue", 100, 44)
    st("pm", 955, 260, "Parse & map", None, "blue", 130, 44)
    d.arrow([(583, 260), (600, 260)], INK_2)
    d.arrow([(720, 260), (750, 260)], INK_2)
    d.arrow([(850, 260), (890, 260)], INK_2)
    st("nr", 1250, 250, "Needs review", "needs_review", "orange", 180)
    st("ver", 1250, 480, "Verified", "verified", "green")
    st("an", 1000, 480, "Analysing", "analysing")
    st("ex", 760, 480, "Explaining", "explaining", "purple")
    st("done", 480, 480, "Explained", "explained", "green", 180)
    st("rej", 190, 480, "Rejected", "rejected", "red")
    st("fail", 760, 660, "Failed", "failed", "red")
    st("del", 480, 660, "Deleted", "deleted · erased", "slate", 180)
    d.circle(190, 660, 12, PAPER, INK, 1.6)
    d.circle(190, 660, 7, INK)

    tr([(81, 250), (105, 250)])
    tr([(275, 250), (335, 250)], "consent ok", (305, 228))
    tr([(505, 250), (540, 250)], "claimed", (520, 215))
    tr([(1060, 250), (1160, 250)], "draft saved", (1110, 228))
    d.arrow([(1340, 240), (1380, 240), (1380, 212), (1290, 212), (1290, 222)], INK_2, sw=1.3)
    d.text(1386, 208, "edit value", 10.5, 500, INK_2)
    tr([(1250, 278), (1250, 452)], "user confirms", (1250, 365))
    tr([(1165, 480), (1085, 480)], "enqueue", (1125, 458))
    tr([(915, 480), (845, 480)], "analysed", (880, 458))
    tr([(675, 480), (570, 480)], "validated", (622, 458))
    d.arrow([(480, 508), (480, 560), (1250, 560), (1250, 508)], INK_2, sw=1.3)
    d.pill(865, 560, "user edits a value → re-analyse")
    tr([(190, 278), (190, 452)], "invalid file / no consent", (190, 365))
    tr([(190, 508), (190, 648)])
    tr([(880, 340), (880, 600), (820, 600), (820, 632)], "3rd failure", (880, 405), RED)
    d.arrow([(700, 340), (700, 380), (420, 380), (420, 278)], INK_2, sw=1.3, dash="5 4")
    d.pill(560, 380, "error · attempts < 3 → retry with back-off")
    tr([(740, 508), (740, 632)], "retries exhausted", (740, 600), RED)
    d.arrow([(845, 660), (1330, 660), (1330, 278)], INK_2, sw=1.3, dash="5 4")
    d.pill(1090, 660, "admin retry")
    tr([(480, 508), (480, 632)], "user deletes", (480, 595))
    tr([(390, 660), (202, 660)], "30-day purge", (300, 638))

    d.card(1010, 700 - 20, 440, 90, "Any state → Deleted", [
        "“Delete report” or “delete profile” is allowed from every state;",
        "files and rows are erased and only an audit entry remains.",
    ], role="slate", glyph="lock")
    d.footer(f"Nabz · docs/diagrams/state-machine.svg · {VERSION}")
    return d


# =============================================================================
# 8. Entity–relationship diagram
# =============================================================================
# Each entity: (domain, [(key, column, type), ...]). Keep in sync with docs/04-data-design.md.
ENTITIES: dict[str, tuple[str, list[tuple[str, str, str]]]] = {
    "app_user": ("slate", [("PK", "id", "uuid"), ("UQ", "email", "citext"), ("", "phone", "text"),
                           ("", "password_hash", "text"), ("", "preferred_language", "lang"),
                           ("", "role", "user_role"), ("", "created_at", "timestamptz"), ("", "deleted_at", "timestamptz")]),
    "consent": ("slate", [("PK", "id", "uuid"), ("FK", "user_id", "uuid"), ("FK", "profile_id", "uuid"),
                          ("", "purpose", "consent_purpose"), ("", "policy_version", "text"),
                          ("", "granted_at", "timestamptz"), ("", "revoked_at", "timestamptz")]),
    "audit_log": ("orange", [("PK", "id", "bigint"), ("FK", "actor_user_id", "uuid"), ("", "action", "text"),
                             ("", "entity_type", "text"), ("", "entity_id", "uuid"), ("", "at", "timestamptz"),
                             ("", "metadata", "jsonb")]),
    "share_link": ("orange", [("PK", "id", "uuid"), ("FK", "report_id", "uuid"), ("FK", "created_by", "uuid"),
                              ("UQ", "token_hash", "text"), ("", "expires_at", "timestamptz"), ("", "revoked_at", "timestamptz")]),
    "profile": ("slate", [("PK", "id", "uuid"), ("FK", "owner_user_id", "uuid"), ("", "display_name", "text"),
                          ("", "sex", "sex"), ("", "date_of_birth", "date"), ("", "relationship", "relationship"),
                          ("", "preferred_language", "lang"), ("", "deleted_at", "timestamptz")]),
    "trend_insight": ("purple", [("PK", "id", "uuid"), ("FK", "profile_id", "uuid"), ("FK", "test_id", "int"),
                                 ("", "n_points", "smallint"), ("", "slope_per_year", "numeric"),
                                 ("", "rcv_significant", "boolean"), ("", "projected_crossing", "date"),
                                 ("", "percentile", "real"), ("", "computed_at", "timestamptz")]),
    "feedback": ("orange", [("PK", "id", "uuid"), ("FK", "explanation_id", "uuid"), ("FK", "user_id", "uuid"),
                            ("", "rating", "smallint"), ("", "comment", "text"), ("", "created_at", "timestamptz")]),
    "report": ("blue", [("PK", "id", "uuid"), ("FK", "profile_id", "uuid"), ("FK", "uploaded_by", "uuid"),
                        ("", "lab_name", "text"), ("", "collected_at", "date"), ("", "status", "report_status"),
                        ("", "source_sha256", "text"), ("", "created_at", "timestamptz"), ("", "deleted_at", "timestamptz")]),
    "report_file": ("blue", [("PK", "id", "uuid"), ("FK", "report_id", "uuid"), ("", "storage_key", "text"),
                             ("", "mime_type", "text"), ("", "size_bytes", "int"), ("", "sha256", "text"),
                             ("", "quality_score", "real")]),
    "report_page": ("blue", [("PK", "id", "uuid"), ("FK", "report_file_id", "uuid"), ("", "page_no", "smallint"),
                             ("", "width", "int"), ("", "height", "int"), ("", "ocr", "jsonb")]),
    "explanation": ("purple", [("PK", "id", "uuid"), ("FK", "report_id", "uuid"), ("", "language", "lang"),
                               ("", "model_id", "text"), ("", "prompt_version", "text"), ("", "content", "jsonb"),
                               ("", "safety_status", "safety_status"), ("", "audio_key", "text"),
                               ("", "input_tokens", "int")]),
    "processing_job": ("blue", [("PK", "id", "bigint"), ("FK", "report_id", "uuid"), ("", "stage", "job_stage"),
                                ("", "status", "job_status"), ("", "attempts", "smallint"), ("", "run_after", "timestamptz"),
                                ("", "locked_at", "timestamptz"), ("", "error", "text")]),
    "observation": ("blue", [("PK", "id", "uuid"), ("FK", "report_id", "uuid"), ("FK", "report_page_id", "uuid"),
                             ("FK", "test_id", "int"), ("", "raw_name", "text"), ("", "raw_value", "text"),
                             ("", "value_num", "numeric"), ("", "unit", "text"), ("", "ref_low", "numeric"),
                             ("", "ref_high", "numeric"), ("", "status", "obs_status"), ("", "bbox", "jsonb"),
                             ("", "confidence", "real"), ("", "verified_at", "timestamptz")]),
    "explanation_citation": ("purple", [("PK", "explanation_id", "uuid"), ("PK", "kb_chunk_id", "uuid"),
                                        ("", "rank", "smallint")]),
    "organ_system": ("green", [("PK", "id", "smallint"), ("UQ", "code", "text"), ("", "name_en", "text"),
                               ("", "name_hi", "text"), ("", "name_or", "text"), ("", "mesh_ids", "text[]")]),
    "lab_test": ("green", [("PK", "id", "int"), ("UQ", "loinc_code", "text"), ("", "canonical_name", "text"),
                           ("", "aliases", "text[]"), ("FK", "organ_system_id", "smallint"), ("", "canonical_unit", "text"),
                           ("", "plausible_min", "numeric"), ("", "plausible_max", "numeric"),
                           ("", "cv_within_subject", "real"), ("", "cv_analytical", "real")]),
    "kb_chunk": ("purple", [("PK", "id", "uuid"), ("FK", "document_id", "uuid"), ("FK", "test_id", "int"),
                            ("", "chunk_index", "smallint"), ("", "content", "text"), ("", "language", "lang"),
                            ("", "embedding", "vector(384)")]),
    "kb_document": ("purple", [("PK", "id", "uuid"), ("", "title", "text"), ("", "source_org", "text"),
                               ("", "url", "text"), ("", "license", "text"), ("", "language", "lang"),
                               ("", "checksum", "text")]),
    "unit_conversion": ("green", [("PK", "id", "int"), ("FK", "test_id", "int"), ("", "from_unit", "text"),
                                  ("", "to_unit", "text"), ("", "factor", "numeric"), ("", "offset", "numeric")]),
    "reference_range": ("green", [("PK", "id", "int"), ("FK", "test_id", "int"), ("", "sex", "sex"),
                                  ("", "age_min", "smallint"), ("", "age_max", "smallint"), ("", "low", "numeric"),
                                  ("", "high", "numeric"), ("", "source", "text")]),
    "critical_limit": ("green", [("PK", "id", "int"), ("FK", "test_id", "int"), ("", "low", "numeric"),
                                 ("", "high", "numeric"), ("", "message_key", "text"), ("", "reviewed_at", "date")]),
    "population_percentile": ("green", [("PK", "id", "int"), ("FK", "test_id", "int"), ("", "sex", "sex"),
                                        ("", "age_band", "int4range"), ("", "p05 … p95", "numeric"),
                                        ("", "source", "text")]),
}
DOMAINS = {"slate": "Identity & consent", "blue": "Reports & extraction", "green": "Clinical catalogue",
           "purple": "Knowledge, AI & analytics", "orange": "Governance"}

ER_W, ER_HEAD, ER_ROW = 240, 30, 18


def er_diagram() -> Diagram:
    cols = [30, 302, 574, 846, 1118, 1390]
    place = {
        "app_user": (0, 110), "consent": (0, 330), "audit_log": (0, 540), "share_link": (0, 760),
        "profile": (1, 110), "trend_insight": (1, 330), "feedback": (1, 780),
        "report": (2, 110), "report_file": (2, 350), "report_page": (2, 550), "explanation": (2, 760),
        "processing_job": (3, 110), "observation": (3, 330), "explanation_citation": (3, 780),
        "organ_system": (4, 110), "lab_test": (4, 290), "kb_chunk": (4, 560), "kb_document": (4, 770),
        "unit_conversion": (5, 110), "reference_range": (5, 290), "critical_limit": (5, 510),
        "population_percentile": (5, 690),
    }
    d = Diagram(1660, 1090, "Nabz — entity–relationship diagram",
                "PostgreSQL 17 schema (logical). Crow's-foot notation. 22 tables in five domains; column lists are abridged.")
    box: dict[str, tuple[float, float, float]] = {}
    for name, (ci, y) in place.items():
        role, cols_ = ENTITIES[name]
        x = cols[ci]
        h = ER_HEAD + len(cols_) * ER_ROW + 8
        box[name] = (x, y, h)
        d.rect(x, y, ER_W, h, fill=PAPER, stroke=EDGE[role], sw=1.4, rx=5)
        d.rect(x, y, ER_W, ER_HEAD, fill=TILE[role], stroke="none", rx=5)
        d.rect(x, y + ER_HEAD - 6, ER_W, 6, fill=TILE[role], stroke="none", rx=0)
        d.text(x + 12, y + 20, name, 12.5, 700, PAPER, family=MONO)
        for i, (k, col, typ) in enumerate(cols_):
            ry = y + ER_HEAD + 4 + i * ER_ROW
            if i % 2 == 1:
                d.rect(x + 1, ry, ER_W - 2, ER_ROW, fill=SNOW, stroke="none", rx=0)
            kc = {"PK": TILE["orange"], "FK": TILE["blue"], "UQ": TILE["green"]}.get(k, MUTED)
            d.text(x + 10, ry + 13, k, 9, 700, kc, family=MONO)
            d.text(x + 36, ry + 13, col, 11, 600 if k == "PK" else 400, INK, family=MONO)
            d.text(x + ER_W - 10, ry + 13, typ, 10, 400, MUTED, "end", family=MONO)

    def row_y(ent: str, column: str) -> float:
        x, y, _ = box[ent]
        idx = [c for _, c, _ in ENTITIES[ent][1]].index(column)
        return y + ER_HEAD + 4 + idx * ER_ROW + ER_ROW / 2

    def left(ent, column):
        return (box[ent][0], row_y(ent, column))

    def right(ent, column):
        return (box[ent][0] + ER_W, row_y(ent, column))

    def top(ent, f=0.5):
        return (box[ent][0] + ER_W * f, box[ent][1])

    def bottom(ent, f=0.5):
        return (box[ent][0] + ER_W * f, box[ent][1] + box[ent][2])

    def end(p, q, kind):
        """Draw a cardinality symbol at p for a line heading towards q."""
        (x1, y1), (x2, y2) = p, q
        ux, uy = (x2 - x1), (y2 - y1)
        ln = (ux * ux + uy * uy) ** 0.5
        ux, uy = ux / ln, uy / ln
        px, py = -uy, ux
        c = INK_2
        parts = []

        def tick(t):
            cx, cy = x1 + ux * t, y1 + uy * t
            parts.append(f"M{cx + px * 6:.1f},{cy + py * 6:.1f} L{cx - px * 6:.1f},{cy - py * 6:.1f}")

        if kind in ("one", "one_many"):
            tick(12)
        if kind == "one":
            tick(17)
        if kind in ("one_many", "zero_many"):
            parts.append(f"M{x1 + px * 7:.1f},{y1 + py * 7:.1f} L{x1 + ux * 10:.1f},{y1 + uy * 10:.1f} "
                         f"L{x1 - px * 7:.1f},{y1 - py * 7:.1f}")
        if kind == "zero_one":
            tick(10)
        d.raw(f'<path d="{" ".join(parts)}" stroke="{c}" stroke-width="1.3" fill="none"/>')
        if kind in ("zero_many", "zero_one"):
            t = 20 if kind == "zero_many" else 19
            d.circle(x1 + ux * t, y1 + uy * t, 4.2, PAPER, c, 1.3)

    def rel(pts, a_kind, b_kind):
        d.arrow(pts, INK_2, sw=1.25, head=None)
        end(pts[0], pts[1], a_kind)
        end(pts[-1], pts[-2], b_kind)

    # identity
    rel([right("app_user", "id"), left("profile", "owner_user_id")], "one", "zero_many")
    rel([bottom("app_user", 0.5), top("consent", 0.5)], "one", "zero_many")
    pc = right("consent", "profile_id")
    rel([pc, (286, pc[1]), (286, row_y("profile", "deleted_at")), left("profile", "deleted_at")], "zero_many", "one")
    au = left("app_user", "role")
    al = left("audit_log", "actor_user_id")
    rel([au, (16, au[1]), (16, al[1]), al], "zero_one", "zero_many")
    # reports
    rel([right("profile", "id"), left("report", "profile_id")], "one", "zero_many")
    rel([bottom("profile", 0.5), top("trend_insight", 0.5)], "one", "zero_many")
    rel([bottom("report", 0.5), top("report_file", 0.5)], "one", "one_many")
    rel([bottom("report_file", 0.5), top("report_page", 0.5)], "one", "one_many")
    rel([right("report", "id"), left("processing_job", "report_id")], "one", "zero_many")
    ro = right("report", "collected_at")
    rel([ro, (830, ro[1]), (830, row_y("observation", "report_id")), left("observation", "report_id")], "one", "zero_many")
    rp = right("report_page", "id")
    rel([rp, (818, rp[1]), (818, row_y("observation", "report_page_id")), left("observation", "report_page_id")],
        "zero_one", "zero_many")
    lo = left("lab_test", "id")
    ot = right("observation", "test_id")
    rel([lo, (1102, lo[1]), (1102, ot[1]), ot], "zero_one", "zero_many")
    rel([bottom("organ_system", 0.5), top("lab_test", 0.5)], "one", "zero_many")
    # catalogue bus
    lt = right("lab_test", "id")
    for ent in ("unit_conversion", "reference_range", "critical_limit", "population_percentile"):
        tgt = left(ent, "test_id")
        rel([lt, (1374, lt[1]), (1374, tgt[1]), tgt], "one", "zero_many")
    rel([bottom("lab_test", 0.5), top("kb_chunk", 0.5)], "zero_one", "zero_many")
    # knowledge & explanation
    rs = left("report", "status")
    ex = left("explanation", "report_id")
    rel([rs, (558, rs[1]), (558, ex[1]), ex], "one", "zero_many")
    ei = right("explanation", "id")
    ce = left("explanation_citation", "explanation_id")
    rel([ei, (830, ei[1]), (830, ce[1]), ce], "one", "zero_many")
    kc = left("kb_chunk", "id")
    ck = right("explanation_citation", "kb_chunk_id")
    rel([kc, (1102, kc[1]), (1102, ck[1]), ck], "one", "zero_many")
    rel([top("kb_document", 0.5), bottom("kb_chunk", 0.5)], "one", "one_many")
    rel([left("explanation", "language"), right("feedback", "explanation_id")], "one", "zero_many")

    # legends
    ly = 1000
    x = 846
    for role, label in DOMAINS.items():
        d.rect(x, ly - 8, 16, 16, fill=TILE[role], stroke="none", rx=3)
        d.text(x + 24, ly + 4, label, 11, 500, INK_2)
        x += 24 + text_width(label, 11) + 26
    lx, lyy = 846, 1040
    for kind, label in [("one", "exactly one"), ("zero_one", "zero or one"), ("one_many", "one or many"),
                        ("zero_many", "zero or many")]:
        d.line(lx, lyy, lx + 40, lyy, INK_2, 1.25)
        end((lx + 40, lyy), (lx, lyy), kind)
        d.text(lx + 50, lyy + 4, label, 11, 400, INK_2)
        lx += 50 + text_width(label, 11) + 34
    d.text(30, 1000 + 4, "Not drawn to keep the figure readable: report.uploaded_by, share_link.created_by and", 10.5, 400, MUTED)
    d.text(30, 1018, "feedback.user_id → app_user · share_link.report_id → report · trend_insight.test_id → lab_test.", 10.5, 400, MUTED)
    d.footer(f"Nabz · docs/diagrams/er-diagram.svg · {VERSION}")
    return d


# =============================================================================
# 9. Class diagram (backend)
# =============================================================================
def class_diagram() -> Diagram:
    d = Diagram(1660, 1300, "Nabz — class diagram (backend core)",
                "Python modules in backend/app. Interfaces keep OCR, LLM, TTS, storage and queue swappable.")
    cols = [30, 300, 570, 840, 1110, 1380]
    W = 250
    B: dict[str, tuple[float, float, float]] = {}

    def cls(key, ci, y, name, attrs, methods, role="blue", stereo=None):
        x = cols[ci]
        hh = 44 if stereo else 30
        h = hh + max(1, len(attrs)) * 16 + 10 + len(methods) * 16 + 10
        d.rect(x, y, W, h, fill=PAPER, stroke=EDGE[role], sw=1.4, rx=4)
        d.rect(x, y, W, hh, fill=EDGE[role], stroke="none", rx=4, opacity=0.18)
        d.rect(x, y, W, 4, fill=TILE[role], stroke="none", rx=2)
        if stereo:
            d.text(x + W / 2, y + 19, f"«{stereo}»", 10, 500, MUTED, "middle")
            d.text(x + W / 2, y + 35, name, 12.5, 700, INK, "middle", italic=stereo == "interface")
        else:
            d.text(x + W / 2, y + 21, name, 12.5, 700, INK, "middle")
        yy = y + hh
        d.line(x, yy, x + W, yy, EDGE[role], 1)
        for i, a in enumerate(attrs or [""]):
            d.text(x + 10, yy + 16 + i * 16, a, 10.3, 400, INK_2, family=MONO)
        yy += max(1, len(attrs)) * 16 + 10
        d.line(x, yy, x + W, yy, EDGE[role], 1)
        for i, m in enumerate(methods):
            d.text(x + 10, yy + 16 + i * 16, m, 10.3, 400, INK, family=MONO)
        B[key] = (x, y, h)

    # row 1 — request path
    cls("router", 0, 100, "ReportsRouter", ["- service: ReportService"],
        ["+ upload(profile_id, file)", "+ get(report_id)", "+ confirm(report_id, edits)", "+ insights(report_id)"],
        "cyan", "FastAPI router")
    cls("service", 1, 100, "ReportService", ["- repo: ReportRepository", "- storage: StorageBackend", "- queue: JobQueue"],
        ["+ create(profile_id, upload): Report", "+ confirm(id, edits): Report", "+ insights(id): Insights",
         "+ delete(id): None"])
    cls("repo", 2, 100, "ReportRepository", ["- session: Session"],
        ["+ get(id): Report", "+ save(report): None", "+ observations(id): list", "+ history(profile, test): Series"])
    cls("storage", 3, 100, "StorageBackend", [], ["+ put(key, data): None", "+ get(key): bytes", "+ delete(key): None"],
        "green", "interface")
    cls("queue", 4, 100, "JobQueue", [], ["+ enqueue(report_id, stage)", "+ claim(worker_id): Job | None",
                                          "+ complete(job)", "+ fail(job, error)"], "green", "interface")
    cls("worker", 5, 100, "Worker", ["- queue: JobQueue", "- handlers: dict[Stage, …]"],
        ["+ run_forever(): None", "+ process(job): None"], "slate")
    # row 2 — implementations
    cls("local", 3, 330, "LocalVolumeStorage", ["- root: Path"], ["+ put / get / delete"], "green")
    cls("pgq", 4, 330, "PgJobQueue", ["- engine: Engine"], ["+ claim(): FOR UPDATE", "     SKIP LOCKED"], "green")
    cls("handler", 5, 330, "StageHandler", ["+ stage: Stage"], ["+ handle(job): None"], "slate", "interface")
    # row 3 — stages
    cls("ocr_if", 0, 580, "OCREngine", [], ["+ read(image): list[Line]"], "teal", "interface")
    cls("extract", 1, 580, "ExtractionStage", ["- ocr: OCREngine", "- matcher: CatalogMatcher", "- scorer: ConfidenceModel"],
        ["+ handle(job): None"], "slate")
    cls("analyse", 2, 580, "AnalysisStage", ["- change: ChangeDetector", "- trends: TrendAnalyzer", "- critical: CriticalRules"],
        ["+ handle(job): None"], "slate")
    cls("explain", 3, 580, "ExplanationStage", ["- retriever: KnowledgeRetriever", "- llm: LLMProvider",
                                                "- validator: SafetyValidator"], ["+ handle(job): None"], "slate")
    cls("narrate", 4, 580, "NarrationStage", ["- tts: TTSProvider"], ["+ handle(job): None"], "slate")
    cls("tts", 5, 580, "TTSProvider", [], ["+ speak(text, lang): bytes"], "purple", "interface")
    # row 4+ — collaborators
    cls("paddle", 0, 810, "PaddleOCREngine", ["- model: PaddleOCR"], ["+ read(image): list[Line]"], "teal")
    cls("matcher", 1, 810, "CatalogMatcher", ["- catalog: TestCatalog", "- llm: LLMProvider"], ["+ match(row): Match"], "teal")
    cls("conf", 1, 990, "ConfidenceModel", ["- clf: CalibratedClassifier"], ["+ score(features): float"], "teal")
    cls("change", 2, 810, "ChangeDetector", ["- cv: BiologicalVariation"], ["+ rcv(test): float",
                                                                          "+ significant(a, b): bool"], "cyan")
    cls("trend", 2, 990, "TrendAnalyzer", [], ["+ slope(series): Trend", "+ project(series, lim): date"], "cyan")
    cls("critical", 2, 1150, "CriticalRules", ["- limits: dict[int, Limit]"], ["+ check(obs): Alert | None"], "red")
    cls("retriever", 3, 810, "KnowledgeRetriever", ["- embedder: Embedder"], ["+ top_k(tests, lang, k): list"], "purple")
    cls("validator", 3, 990, "SafetyValidator", ["- rules: list[Rule]"], ["+ validate(text, obs): Verdict"], "red")
    cls("llm", 4, 810, "LLMProvider", [], ["+ complete(prompt, schema): dict"], "purple", "interface")
    cls("anthropic", 4, 1010, "GroqProvider", ['- model = "openai/gpt-oss-120b"'], ["+ complete(prompt, schema)"], "purple")
    cls("ollama", 5, 1010, "OllamaProvider", ['- model = "qwen3:4b"'], ["+ complete(prompt, schema)"], "purple")

    def R(k, f=0.5):  # right-edge point at fraction f of height
        x, y, h = B[k]
        return (x + W, y + h * f)

    def L(k, f=0.5):
        x, y, h = B[k]
        return (x, y + h * f)

    def T(k, f=0.5):
        x, y, h = B[k]
        return (x + W * f, y)

    def Bo(k, f=0.5):
        x, y, h = B[k]
        return (x + W * f, y + h)

    assoc = dict(color=INK_2, sw=1.3, head="open")
    use = dict(color=INK_2, sw=1.2, head="open", dash="5 4")
    real = dict(color=INK_2, sw=1.2, head="triangle", dash="6 4")

    d.arrow([R("router", 0.35), L("service", 0.35)], **assoc)
    d.arrow([R("service", 0.35), L("repo", 0.35)], **assoc)
    d.arrow([T("service", 0.5), (425, 86), (965, 86), T("storage", 0.5)], **assoc)
    d.arrow([T("service", 0.5), (425, 86), (1235, 86), T("queue", 0.5)], **assoc)
    d.arrow([L("worker", 0.35), R("queue", 0.35)], **assoc)
    d.arrow([Bo("worker"), T("handler")], color=INK_2, sw=1.3, head="open", tail="diamond")
    d.pill(1505, 300, "handlers 1..*", MUTED, 10)
    d.arrow([T("local"), Bo("storage")], **real)
    d.arrow([T("pgq"), Bo("queue")], **real)
    # stages realise StageHandler via a shared bus
    bus_y = 545
    hb = Bo("handler")
    for k in ("extract", "analyse", "explain", "narrate"):
        t = T(k)
        d.arrow([t, (t[0], bus_y)], color=INK_2, sw=1.2, head=None, dash="6 4")
    d.arrow([(T("extract")[0], bus_y), (hb[0], bus_y), hb], **real)
    # uses
    d.arrow([L("extract", 0.4), R("ocr_if", 0.4)], **use)
    d.arrow([T("paddle"), Bo("ocr_if")], **real)
    d.arrow([Bo("extract"), T("matcher")], **use)
    le = L("extract", 0.8)
    d.arrow([le, (286, le[1]), (286, L("conf")[1]), L("conf")], **use)
    d.arrow([Bo("analyse"), T("change")], **use)
    la = L("analyse", 0.8)
    for k in ("trend", "critical"):
        d.arrow([la, (556, la[1]), (556, L(k)[1]), L(k)], **use)
    d.arrow([Bo("explain", 0.3), T("retriever", 0.3)], **use)
    lx = L("explain", 0.85)
    d.arrow([lx, (826, lx[1]), (826, L("validator")[1]), L("validator")], **use)
    rx = R("explain", 0.85)
    d.arrow([rx, (1096, rx[1]), (1096, L("llm")[1]), L("llm")], **use)
    d.arrow([R("narrate", 0.5), L("tts", 0.5)], **use)
    d.arrow([T("anthropic"), Bo("llm")], **real)
    ro = T("ollama")
    d.arrow([ro, (ro[0], 1000 - 14), (1380 + 30, 1000 - 14), (1380 + 30, R("llm")[1]), R("llm")], **real)
    mt = T("matcher", 0.8)
    d.arrow([mt, (mt[0], 780), (1110 + W * 0.3, 780), T("llm", 0.3)], color=PURPLE, sw=1.2, head="open", dash="5 4")
    d.pill(760, 780, "fallback: local model", TILE["purple"], 10)

    d.legend(840, 1240, [("line", INK_2, "association"), ("dash", INK_2, "dependency «use»")])
    d.raw(f'<path d="M1180,1266 h26" stroke="{INK_2}" stroke-width="1.2" stroke-dasharray="6 4" '
          f'marker-end="url(#{d._marker(INK_2, "triangle")})"/>')
    d.text(1214, 1270, "realisation", 11, 400, INK_2)
    d.raw(f'<path d="M1320,1266 h26" stroke="{INK_2}" stroke-width="1.3" marker-start="url(#{d._marker(INK_2, "diamond")})"/>')
    d.text(1354, 1270, "composition", 11, 400, INK_2)
    d.footer(f"Nabz · docs/diagrams/class-diagram.svg · {VERSION}")
    return d


# =============================================================================
# 10. Gantt chart (from schedule.csv)
# =============================================================================
OWNER = {"DEV": ("blue", "Developer"), "TEAM": ("purple", "Team members"), "ALL": ("green", "Whole team")}


def gantt() -> Diagram:
    rows = list(csv.DictReader((SRC / "schedule.csv").open(encoding="utf-8")))
    for r in rows:
        r["s"] = date.fromisoformat(r["start"])
        r["e"] = date.fromisoformat(r["end"])
    start = min(r["s"] for r in rows)
    end = max(r["e"] for r in rows)
    days = (end - start).days + 1
    x0, x1 = 500, 1630
    px = (x1 - x0) / days
    rh, top = 27, 150
    H = top + len(rows) * rh + 150
    d = Diagram(1660, H, "Nabz — project schedule (Gantt)",
                f"{start.day} {start:%b} – {end.day} {end:%b %Y} · one-week sprints · "
                "generated from docs/diagrams/src/schedule.csv")

    def X(dt: date) -> float:
        return x0 + (dt - start).days * px

    # calendar header
    d.rect(30, top - 56, x1 - 30, 56, fill=SNOW, stroke="none", rx=4)
    d.text(44, top - 22, "ID", 11, 700, MUTED)
    d.text(96, top - 22, "Task", 11, 700, MUTED)
    d.text(418, top - 22, "Owner", 11, 700, MUTED)
    month = None
    for i in range(days):
        dt = start + timedelta(days=i)
        if dt.weekday() >= 5:
            d.rect(X(dt), top, px, len(rows) * rh, fill=SNOW, stroke="none", rx=0)
        if dt.month != month:
            month = dt.month
            nxt = date(dt.year + (dt.month == 12), dt.month % 12 + 1, 1)
            room = (min(nxt, end + timedelta(days=1)) - dt).days
            d.text(X(dt) + 4, top - 38, f"{dt:%B %Y}" if room >= 10 else f"{dt:%b}", 11.5, 700, INK)
            d.line(X(dt), top - 56, X(dt), top, LINE, 1)
        if dt.weekday() == 0:
            wk = (dt - start).days // 7
            d.line(X(dt), top - 30, X(dt), top + len(rows) * rh, LINE, 1)
            d.text(X(dt) + 4, top - 18, f"W{wk}", 10.5, 700, INK_2)
            d.text(X(dt) + 10 + 1.15 * text_width(f"W{wk}", 10.5, 700), top - 18, f"{dt:%d %b}", 10, 400, MUTED)

    for i, r in enumerate(rows):
        y = top + i * rh
        kind = r["kind"]
        if kind == "phase":
            d.rect(30, y, x1 - 30, rh, fill=SNOW_2, stroke="none", rx=0, opacity=0.7)
            d.text(44, y + 18, r["id"], 11, 700, INK, family=MONO)
            d.text(96, y + 18, r["phase"], 12, 700, INK)
            xs, xe = X(r["s"]), X(r["e"]) + px
            d.raw(f'<path d="M{xs:.1f},{y + 18} V{y + 9} H{xe:.1f} V{y + 18}" fill="none" stroke="{INK}" '
                  f'stroke-width="3" stroke-linejoin="round"/>')
            continue
        d.line(30, y + rh, x1, y + rh, SNOW_2, 1)
        d.text(44, y + 18, r["id"], 10.5, 500, MUTED, family=MONO)
        d.text(96, y + 18, r["task"], 11.5, 600 if kind == "milestone" else 400, INK)
        role, who = OWNER[r["owner"]]
        if kind == "milestone":
            cx = X(r["e"]) + px / 2
            d.raw(f'<path d="M{cx},{y + 5} L{cx + 9},{y + 14} L{cx},{y + 23} L{cx - 9},{y + 14} z" '
                  f'fill="{TILE["orange"]}"/>')
            d.text(cx + 14, y + 18, f"{r['e']:%a %d %b}", 10.5, 600, TILE["orange"])
            d.text(418, y + 18, "gate", 10.5, 600, TILE["orange"])
            continue
        d.rect(412, y + 6, 70, 16, fill=EDGE[role], stroke="none", rx=8, opacity=0.25)
        d.text(447, y + 18, r["owner"], 9.5, 700, TILE[role], "middle")
        xs, xe = X(r["s"]), X(r["e"]) + px
        if kind == "buffer":
            d.rect(xs, y + 7, xe - xs, 14, fill=PAPER, stroke=MUTED, sw=1, rx=4, dash="3 3")
        else:
            d.rect(xs, y + 7, xe - xs, 14, fill=TILE[role], stroke="none", rx=4)
        dur = (r["e"] - r["s"]).days + 1
        d.text(xe + 6, y + 18, f"{dur}d", 9.5, 500, MUTED)

    # status line
    ly = top + len(rows) * rh + 34
    d.legend(40, ly, [("box", TILE["blue"], "Developer (build)"), ("box", TILE["purple"], "Team members (research, content, pitch)"),
                      ("box", TILE["green"], "Whole team"), ("box", SNOW, "weekend")])
    d.raw(f'<path d="M{1045},{ly - 9} l9,9 -9,9 -9,-9 z" fill="{TILE["orange"]}"/>')
    d.text(1062, ly + 4, "milestone / gate", 11, 400, INK_2)
    d.text(40, ly + 36, "Public holidays (Independence Day, Ganesh Chaturthi, Nuakhai) are planned at reduced capacity; the "
                        "two-day buffer after the demo gate absorbs small slips.", 11, 400, MUTED)
    d.footer(f"Nabz · docs/diagrams/gantt.svg · {VERSION}")
    return d


# =============================================================================
# 11. Project life cycle
# =============================================================================
def lifecycle() -> Diagram:
    d = Diagram(1480, 820, "Nabz — project life cycle",
                "Iterative-incremental model: RUP-style phases with one-week Scrum-style sprints and a quality gate at the end of each phase.")
    phases = [
        ("Inception", "1 – 9 Aug", "slate", ["Problem & persona validation", "Charter, SRS, architecture", "Risk register, test plan",
                                                  "Repo + Docker scaffold"], "M0 · docs baseline"),
        ("Elaboration", "10 – 16 Aug", "cyan", ["Test catalogue (60 tests)", "Synthetic report generator", "3D anatomy spike",
                                               "Knowledge sources + licences"], "risks retired"),
        ("Construction", "17 Aug – 20 Sep", "blue", ["S2–S3 extraction + review UI", "S4 analytics engine",
                                                      "S5 grounded explanations", "S6 3D body map + accounts"],
         "M1 · 30 Aug  ·  M2 · 20 Sep"),
        ("Transition", "21 – 30 Sep", "green", ["S7 evaluation + hardening", "User tests + doctor review", "Report, poster, rehearsal",
                                                    "Offline demo mode"], "M3 · demo ready"),
    ]
    x, y, w, h = 40, 110, 340, 64
    for i, (name, when, role, acts, gate) in enumerate(phases):
        px_ = x + i * (w + 10)
        tip = 22
        pts = f"{px_},{y} {px_ + w},{y} {px_ + w + tip},{y + h / 2} {px_ + w},{y + h} {px_},{y + h}"
        if i > 0:
            pts += f" {px_ + tip},{y + h / 2}"
        d.raw(f'<polygon points="{pts}" fill="{TILE[role]}"/>')
        d.text(px_ + (40 if i else 22), y + 29, name, 16, 700, PAPER)
        d.text(px_ + (40 if i else 22), y + 48, when, 11.5, 500, PAPER)
        cy = y + h + 24
        d.rect(px_, cy, w, 190, fill=PAPER, stroke=LINE, rx=8)
        d.text(px_ + 18, cy + 28, "Key activities", 11, 700, MUTED)
        for j, a in enumerate(acts):
            d.circle(px_ + 24, cy + 50 + j * 26, 3.5, TILE[role])
            d.text(px_ + 36, cy + 54 + j * 26, a, 12, 400, INK)
        gy = cy + 214
        d.raw(f'<path d="M{px_ + 24},{gy - 11} l11,11 -11,11 -11,-11 z" fill="{TILE["orange"]}"/>')
        d.text(px_ + 44, gy + 4, gate, 12, 650, INK)

    # sprint loop
    lx, ly = 740, 560
    d.rect(40, 470, 1400, 250, fill=SNOW, stroke="none", rx=10)
    d.text(60, 500, "Inside every construction sprint (1 week)", 13, 700, INK)
    steps = [("Plan", "Mon", "calendar", "pick stories from the backlog;", "define done"),
             ("Build", "Mon–Thu", "api", "feature branch, tests first", "for core logic"),
             ("Verify", "Thu–Fri", "check", "unit + integration tests,", "evaluation scripts"),
             ("Demo & review", "Sat", "users", "show the team; guide review", "every second week"),
             ("Retrospect", "Sun", "chart", "update risks, docs and", "the Gantt chart")]
    for i, (nm, when, gl, l1, l2) in enumerate(steps):
        sx = 70 + i * 272
        d.rect(sx, 520, 238, 150, fill=PAPER, stroke=LINE, rx=8)
        d.rect(sx + 16, 536, 36, 36, fill=TILE["blue"], stroke="none", rx=7)
        d.raw(icon(gl, sx + 24, 544, 20))
        d.text(sx + 64, 552, nm, 13.5, 700, INK)
        d.text(sx + 64, 568, when, 11, 500, MUTED)
        d.lines(sx + 18, 604, [l1, l2], 11.5, 400, INK_2)
        if i < len(steps) - 1:
            d.arrow([(sx + 242, 595), (sx + 268, 595)], INK_2)
    d.arrow([(70 + 4 * 272 + 119, 674), (70 + 4 * 272 + 119, 700), (189, 700), (189, 674)], INK_2, dash="5 4")
    d.pill(700, 700, "repeat for sprints 2 – 7", INK_2)

    d.text(40, 760, "Why this model: requirements for the AI parts are uncertain (OCR accuracy, language quality), so risky "
                    "pieces are prototyped first (Elaboration) and", 11.5, 400, INK_2)
    d.text(40, 778, "every sprint ends with something demonstrable. Documentation is a living baseline: each gate re-publishes "
                    "the docs with an updated revision history.", 11.5, 400, INK_2)
    d.footer(f"Nabz · docs/diagrams/lifecycle.svg · {VERSION}")
    return d


# =============================================================================
# 12. User journey map
# =============================================================================
def journey() -> Diagram:
    d = Diagram(1480, 780, "Nabz — user journey map",
                "Persona: Priya, 29, software engineer in Bengaluru, manages the lab reports of her father Ramesh, 58, who lives in Bhubaneswar.")
    stages = ["Report arrives", "Upload", "Check values", "Understand", "Act", "Track over time"]
    x0, cw = 250, 200
    rows_y = {"doing": 162, "thinking": 262, "feeling": 362, "pain": 520, "nabz": 620}
    bh = 84
    # persona card
    d.rect(30, 100, 200, 604, fill=SNOW, stroke="none", rx=10)
    d.rect(50, 120, 52, 52, fill=TILE["slate"], stroke="none", rx=26)
    d.raw(icon("user", 62, 132, 28))
    y = 198
    for head, body in [("Priya · caregiver", ["Checks reports on her", "phone between meetings.",
                                               "Reads English; her", "father prefers Odia."]),
                       ("Goal", ["Know whether anything", "needs a doctor before", "the next visit."]),
                       ("Frustration", ["Reports are dense tables;", "searching each value is", "slow and frightening."]),
                       ("Ramesh · patient", ["Borderline blood sugar;", "yearly health check-up."])]:
        d.text(50, y, head, 12.5, 700, INK)
        y = d.lines(50, y + 19, body, 11.5, 400, INK_2) + 16
    for i, s in enumerate(stages):
        cx = x0 + i * cw
        d.rect(cx, 100, cw - 8, 40, fill=TILE["blue"], stroke="none", rx=6)
        d.text(cx + (cw - 8) / 2, 125, f"{i + 1} · {s}", 12.5, 700, PAPER, "middle")
    labels = [("doing", "Doing"), ("thinking", "Thinking"), ("feeling", "Feeling"), ("pain", "Pain points"),
              ("nabz", "How Nabz helps")]
    for key, lab in labels:
        d.text(x0 - 10, rows_y[key] + 4, "", 1)
    doing = [["Lab sends a PDF on", "WhatsApp; father", "forwards a photo."], ["Opens Nabz, picks", "Father's profile,", "shares the PDF."],
             ["Sees each value next", "to the report image;", "fixes one OCR error."], ["Taps the glowing liver;", "reads why ALT is high;", "plays Odia audio."],
             ["Books a follow-up;", "shares a summary", "link with the doctor."], ["Uploads next year's", "report; scrubs the", "timeline."]]
    thinking = [["“Is anything here", "serious?”"], ["“Will this work with", "a blurry photo?”"], ["“Can I trust what", "it read?”"],
                ["“What does this", "actually mean for", "Papa?”"], ["“What should I ask", "the doctor?”"], ["“Is his sugar", "getting worse?”"]]
    pain = [["20+ unfamiliar", "abbreviations"], ["photos are skewed,", "shadowed"], ["OCR mistakes would", "mislead"],
            ["search results are", "alarming, generic"], ["5-minute consultation;", "forgets questions"], ["reports from different", "labs, units differ"]]
    nabz = [["body map shows what", "matters at a glance"], ["quality check with", "retake tips"], ["human review of low-", "confidence values"],
            ["grounded explanation", "in Odia, with sources"], ["printable doctor", "questions + share link"], ["unit-normalised trends", "+ change significance"]]
    for i in range(6):
        cx = x0 + i * cw
        d.card(cx, rows_y["doing"] - 12, cw - 8, bh, "", None, accent=False)
        d.lines(cx + 14, rows_y["doing"] + 14, doing[i], 11.5, 400, INK)
        d.rect(cx, rows_y["thinking"] - 12, cw - 8, bh, fill=SNOW, stroke="none", rx=8)
        d.lines(cx + 14, rows_y["thinking"] + 14, thinking[i], 12, 400, INK_2)
        d.rect(cx, rows_y["pain"] - 12, cw - 8, bh, fill=PAPER, stroke=EDGE["red"], sw=1.1, rx=8)
        d.lines(cx + 14, rows_y["pain"] + 14, pain[i], 11.5, 400, INK)
        d.rect(cx, rows_y["nabz"] - 12, cw - 8, bh, fill=EDGE["green"], stroke="none", rx=8, opacity=0.18)
        d.lines(cx + 14, rows_y["nabz"] + 14, nabz[i], 11.5, 600, INK)
    for key, lab in labels:
        d.text(x0 + 6 * cw + 4, rows_y[key] + 4, "", 1)
    # row titles (vertical labels on the right)
    for key, lab in labels:
        yy = rows_y[key] + (54 if key == "feeling" else 30)
        d.raw(f'<text x="{x0 + 6 * cw + 18}" y="{yy}" font-size="11.5" font-weight="700" fill="{MUTED}" '
              f'transform="rotate(90 {x0 + 6 * cw + 18} {yy})" text-anchor="middle">{lab}</text>')
    # emotion curve
    base, amp = rows_y["feeling"] + 45, 55
    before = [-0.6, -0.2, -0.3, -0.9, -0.5, -0.7]
    after = [-0.4, 0.2, 0.3, 0.7, 0.8, 0.9]
    d.rect(x0, rows_y["feeling"] - 12, 6 * cw - 8, 132, fill=PAPER, stroke=LINE, rx=8)
    d.line(x0 + 10, base, x0 + 6 * cw - 18, base, LINE, 1, "4 4")
    d.text(x0 + 12, base - amp + 4, "calm", 10, 500, MUTED)
    d.text(x0 + 12, base + amp - 2, "anxious", 10, 500, MUTED)

    def curve(vals, color, dash=None):
        pts = [(x0 + i * cw + (cw - 8) / 2, base - v * amp) for i, v in enumerate(vals)]
        path = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            mx = (xa + xb) / 2
            path += f" C{mx:.1f},{ya:.1f} {mx:.1f},{yb:.1f} {xb:.1f},{yb:.1f}"
        da = f' stroke-dasharray="{dash}"' if dash else ""
        d.raw(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.5"{da}/>')
        for xp, yp in pts:
            d.circle(xp, yp, 5, PAPER, color, 2)

    curve(before, TILE["red"], "6 5")
    curve(after, TILE["green"])
    d.legend(x0 + 90, rows_y["feeling"] + 106, [("dash", TILE["red"], "today (PDF + web search)"),
                                                 ("line", TILE["green"], "with Nabz")])
    d.footer(f"Nabz · docs/diagrams/user-journey.svg · {VERSION}")
    return d


def _wrap(s: str, width: int) -> list[str]:
    words, rows, cur = s.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            rows.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    rows.append(cur)
    return rows


# =============================================================================
DIAGRAMS = {
    "architecture": architecture,
    "deployment": deployment,
    "pipeline": pipeline,
    "use-case": use_case,
    "activity": activity,
    "sequence": sequence,
    "state-machine": state_machine,
    "er-diagram": er_diagram,
    "class-diagram": class_diagram,
    "gantt": gantt,
    "lifecycle": lifecycle,
    "user-journey": journey,
}


def main(names: list[str]) -> None:
    for name in names or DIAGRAMS:
        DIAGRAMS[name]().save(OUT / f"{name}.svg")
        print(f"wrote docs/diagrams/{name}.svg")


if __name__ == "__main__":
    main(sys.argv[1:])
