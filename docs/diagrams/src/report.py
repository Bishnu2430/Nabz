"""Report edition of the Nabz figures — drawn at printed size for the A4 college report.

    python docs/diagrams/src/report.py            # all figures → docs/diagrams/report/
    python docs/diagrams/src/report.py er-a gantt # a subset

Page geometry (A4, 1-inch margins): the text block is 15.9 cm × 24.6 cm, i.e.
602 × 930 px at 96 px/in. Portrait figures are 602 px wide; landscape figures
(placed on a landscape page) are 930 px wide and at most ~560 px tall.
Figures are written with physical sizes (cm), so inserting them into Word at
100 % gives the intended print size. At that size the smallest text is
9.5 px ≈ 7 pt and body labels are 10.5–12.5 px ≈ 8–9.5 pt.

No titles are drawn inside the figures: the report adds a numbered caption
below each figure, as the college template requires.
"""

from __future__ import annotations

import csv
import sys
from datetime import date, timedelta
from pathlib import Path

from build import (
    DOMAINS, ENTITIES, KIND, OWNER, SRC, _wrap, actor, usecase,
)
from nordsvg import (
    EDGE, INK, INK_2, LINE, MONO, MUTED, PAPER, PURPLE, RED, SNOW, SNOW_2, TILE,
    Diagram, icon, text_width,
)

OUT = SRC.parent / "report"
PW, LW = 602, 930          # portrait / landscape text-block width in px


def page(w: int, h: int) -> Diagram:
    return Diagram(w, h, physical=True, margin=0)


def chip(d: Diagram, x: float, y: float, glyph: str, role: str, label: str,
         sub: str | None = None, size: int = 34) -> None:
    """Icon tile with the label to its right — compact alternative to Diagram.node."""
    d.rect(x, y, size, size, fill=TILE[role], stroke="none", rx=6)
    g = size * 0.6
    d.raw(icon(glyph, x + (size - g) / 2, y + (size - g) / 2, g, width=1.7))
    d.text(x + size + 9, y + (14 if sub else 21), label, 11.5, 650, INK)
    if sub:
        d.text(x + size + 9, y + 28, sub, 10, 400, MUTED)


# =============================================================================
# Architecture (block diagram) — portrait
# =============================================================================
def architecture() -> Diagram:
    d = page(PW, 640)
    chip(d, 72, 6, "users", "slate", "Users", "patients · caregivers · administrators")
    d.group(10, 70, 582, 450, "Docker host", "slate", "laptop", tint=False, sublabel="one Compose project")
    d.group(24, 108, 180, 400, "Presentation", "cyan", "browser")
    d.group(212, 108, 176, 400, "Application", "blue", "api")
    d.group(396, 108, 182, 400, "Data & processing", "green", "database")
    s = 40
    d.node(89, 190, "Web app", "browser", "cyan", ["React + TypeScript", "3D body map · i18n"], s)
    d.node(89, 370, "3D anatomy", "body", "cyan", ["organ meshes (GLB)"], s)
    d.node(300, 190, "API", "api", "blue", ["FastAPI · REST", "auth · consent"], s)
    d.node(300, 370, "Uploads volume", "disk", "blue", ["report files"], s)
    d.node(487, 190, "PostgreSQL 17", "database", "green", ["+ pgvector", "records · jobs · vectors"], s)
    d.node(487, 330, "Worker", "gear", "green", ["OCR · parse · analyse", "explain · narrate"], s)
    d.node(487, 445, "Ollama", "sparkle", "purple", ["local 3–4B · optional"], s)
    c = INK_2
    d.arrow([(89, 40), (89, 170)], c)
    d.arrow([(109, 190), (280, 190)], c, tail="arrow")
    d.pill(195, 190, "REST / JSON")
    d.arrow([(320, 190), (467, 190)], c)
    d.pill(394, 190, "SQL")
    d.arrow([(300, 250), (300, 350)], c)
    d.pill(300, 300, "store file")
    d.arrow([(487, 310), (487, 252)], c, tail="arrow")
    d.pill(487, 281, "jobs · results")
    d.arrow([(467, 336), (400, 336), (400, 370), (320, 370)], c)
    d.pill(420, 356, "read")
    d.arrow([(89, 250), (89, 350)], c, dash="5 4")
    d.arrow([(487, 385), (487, 425)], PURPLE, dash="5 4")
    d.arrow([(507, 330), (585, 330), (585, 556)], TILE["orange"])
    d.group(10, 540, 582, 92, "External APIs", "orange", "cloud", dashed=True,
            sublabel="HTTPS · de-identified values only")
    chip(d, 40, 580, "sparkle", "orange", "LLM API", "gpt-oss-120b on Groq · explanations")
    chip(d, 330, 580, "speaker", "orange", "TTS API", "narration (optional)")
    return d


# =============================================================================
# Deployment — portrait
# =============================================================================
def deployment() -> Diagram:
    d = page(PW, 560)
    d.group(6, 6, 590, 440, "Developer laptop", "slate", "laptop", tint=False, sublabel="Windows 11 · 16 GB RAM · no GPU")
    d.group(20, 46, 562, 388, "Docker Desktop", "slate", "cube", dashed=True, tint=False, sublabel="WSL 2 · 10 GB limit")
    d.group(34, 86, 534, 254, "Compose project nabz", "blue", "network", dashed=True)

    def box(x, y, name, glyph, role, rows, dashed=False):
        d.rect(x, y, 160, 88, fill=PAPER, stroke=EDGE[role], sw=1.3, rx=6, dash="5 4" if dashed else None)
        d.rect(x + 10, y + 10, 24, 24, fill=TILE[role], stroke="none", rx=5)
        d.raw(icon(glyph, x + 14, y + 14, 16))
        d.text(x + 42, y + 27, name, 12, 700, INK, family=MONO)
        for i, r in enumerate(rows):
            d.text(x + 12, y + 52 + i * 15, r, 10, 400, INK_2)

    box(48, 126, "web", "browser", "cyan", ["node:22-alpine · Vite", "127.0.0.1:5173"])
    box(222, 126, "api", "api", "blue", ["python:3.12 + uv · FastAPI", "127.0.0.1:8000"])
    box(396, 126, "worker", "gear", "blue", ["same image as api", "no published port"])
    box(222, 236, "db", "database", "green", ["pgvector/pgvector:pg17", "127.0.0.1:5433 → 5432"])
    box(396, 236, "ollama", "sparkle", "purple", ["qwen3:4b · profile", "local-llm (opt-in)"], dashed=True)
    d.rect(48, 236, 160, 88, fill=SNOW, stroke="none", rx=6)
    d.text(60, 258, "Named volumes", 11, 700, INK)
    d.lines(60, 278, ["pgdata ← db", "uploads ← api, worker", "model-cache ← worker", "ollama ← ollama"],
            10, 400, INK_2, leading=1.35)
    d.arrow([(208, 170), (222, 170)], INK_2)
    d.arrow([(302, 214), (302, 236)], INK_2)
    d.arrow([(476, 214), (476, 225), (342, 225), (342, 236)], INK_2)
    d.text(48, 364, "Published ports — bound to 127.0.0.1, not reachable from the LAN", 10.5, 650, INK_2)
    for i, (p, s_) in enumerate([(":5173", "web"), (":8000", "api"), (":5433", "db"), (":11434", "ollama")]):
        x = 48 + i * 130
        d.rect(x, 376, 120, 26, fill=SNOW, stroke=LINE, rx=13)
        d.text(x + 12, 393, p, 10.5, 700, INK, family=MONO)
        d.text(x + 64, 393, s_, 10.5, 400, INK_2)
    d.arrow([(556, 170), (574, 170), (574, 476)], TILE["orange"])
    d.group(6, 462, 590, 90, "Egress · HTTPS 443", "orange", "globe", dashed=True)
    chip(d, 30, 502, "sparkle", "orange", "LLM API", "explanations")
    chip(d, 222, 502, "speaker", "orange", "TTS API", "optional")
    chip(d, 400, 502, "cloud", "orange", "Model registries", "first run only")
    return d


# =============================================================================
# Pipeline — portrait (three columns)
# =============================================================================
def pipeline() -> Diagram:
    cols = [
        ("A · Ingest & extract", "automatic", [
            ("Upload & validate", "rule", "type · size · quality score", "FastAPI · OpenCV"),
            ("Pre-process", "rule", "deskew · denoise · crop", "OpenCV"),
            ("OCR", "ml", "text layer, else OCR", "pypdfium2 · RapidOCR"),
            ("Parse rows", "rule", "name · value · unit · range", "layout rules"),
            ("Map to catalogue", "ml", "aliases → LOINC codes", "pg_trgm · Qwen3-4B"),
            ("Normalise & score", "ml", "units · plausibility", "scikit-learn"),
        ]),
        ("B · Verify & analyse", "user confirms first", [
            ("Human review", "human", "low confidence first", "web app"),
            ("Classify", "rule", "low · normal · high", "Python rules"),
            ("Critical values", "rule", "fixed urgent message", "reviewed table"),
            ("Change & trend", "ml", "RCV · Theil–Sen slope", "SciPy · statsmodels"),
            ("Percentile", "ml", "vs age band and sex", "NHANES tables"),
        ]),
        ("C · Explain & present", "grounded · validated", [
            ("Retrieve", "ml", "top-k cited passages", "pgvector · e5-small"),
            ("Explain", "genai", "summary + doctor questions", "gpt-oss-120b · Groq"),
            ("Safety check", "rule", "no diagnosis · numbers match", "validator + judge"),
            ("Narrate", "genai", "English · Hindi · Odia", "TTS API"),
            ("Render", "rule", "3D organ status · timeline", "React Three Fiber"),
        ]),
    ]
    d = page(PW, 612)
    cw, ch, step, top = 190, 62, 76, 58
    n = 0
    for c, (title, sub, stages) in enumerate(cols):
        x = 4 + c * 200
        pts = f"{x},4 {x + cw},4 {x + cw + 8},22 {x + cw},40 {x},40"
        d.raw(f'<polygon points="{pts}" fill="{TILE["slate"]}"/>')
        d.text(x + 10, 21, title, 11.5, 700, PAPER)
        d.text(x + 10, 34, sub, 9.5, 400, SNOW_2)
        for i, (name, kind, detail, tech) in enumerate(stages):
            n += 1
            y = top + i * step
            role = KIND[kind][0]
            d.rect(x, y, cw, ch, fill=PAPER, stroke=LINE, rx=6)
            d.rect(x, y, 4, ch, fill=TILE[role], stroke="none", rx=2)
            d.step(x + 20, y + 18, n, TILE[role])
            d.text(x + 37, y + 22, name, 11.5, 650, INK)
            d.text(x + 12, y + 40, detail, 10, 400, INK_2)
            d.text(x + 12, y + 54, tech, 9.5, 500, MUTED, family=MONO)
            if i < len(stages) - 1:
                d.arrow([(x + cw / 2, y + ch + 1), (x + cw / 2, y + step - 1)], INK_2, sw=1.2)
    y = top + 6 * step - 4
    d.pill(301, y + 8, "rows with confidence < τ are reviewed first · only de-identified values leave the host",
           TILE["slate"], 10)
    d.legend(10, y + 38, [("box", TILE[r], lbl) for r, lbl in KIND.values()])
    return d


# =============================================================================
# Use-case model — portrait
# =============================================================================
def use_case() -> Diagram:
    d = page(PW, 760)
    d.rect(96, 4, 432, 690, fill=SNOW, stroke=INK_2, sw=1.2, rx=8, opacity=0.5)
    d.text(110, 22, "Nabz", 12.5, 700, INK)
    a, b, rx, ry = 208, 420, 94, 22
    col_a = [("UC-01", "Sign up / sign in"), ("UC-02", "Manage family profiles"), ("UC-04", "Upload a lab report"),
             ("UC-05", "Review & correct values"), ("UC-06", "Explore 3D body map"), ("UC-07", "View trends"),
             ("UC-08", "Read the explanation"), ("UC-11", "Share with a doctor"), ("UC-12", "Export / delete data")]
    ys = [52 + i * 56 for i in range(9)]

    def uc(cx, cy, code, name, role="blue"):
        d.raw(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{PAPER}" stroke="{EDGE[role]}" stroke-width="1.4"/>')
        d.text(cx, cy - 3, code, 9.5, 600, TILE[role], "middle")
        d.text(cx, cy + 11, name, 10.5, 600, INK, "middle")

    for (code, name), y in zip(col_a, ys):
        uc(a, y, code, name)
    actor(d, 44, 300, "Patient /")
    d.text(44, 360, "caregiver", 12.5, 650, INK, "middle")
    for y in ys:
        d.line(62, 284, a - rx, y, INK_2, 1.1)
    col_b = {"UC-14": ("Curate test catalogue", 52, "orange"), "UC-15": ("Manage knowledge base", 108, "orange"),
             "UC-03": ("Give / withdraw consent", 164, "green"), "UC-13": ("Critical-value alert", 220, "red"),
             "UC-16": ("Audit & safety reports", 276, "orange"), "UC-10": ("Questions for the doctor", 332, "blue"),
             "UC-18": ("Grounded explanation", 388, "purple"), "UC-09": ("Listen to explanation", 444, "purple"),
             "UC-17": ("View shared summary", 584, "cyan")}
    for code, (name, y, role) in col_b.items():
        uc(b, y, code, name, role)

    def dep(p1, p2, kind, lx, ly):
        d.arrow([p1, p2], INK_2, sw=1.1, dash="4 3", head="open")
        d.pill(lx, ly, kind, MUTED, 9.5)

    dep((a + rx, 164), (b - rx, 164), "«include»", 314, 164)
    dep((b - rx, 220), (a + rx, 220), "«extend»", 314, 220)
    dep((a + 80, 385), (b - 88, 340), "«include»", 314, 356)
    dep((a + rx, 388), (b - rx, 388), "«include»", 314, 394)
    dep((b - 88, 452), (a + 80, 399), "«extend»", 314, 430)
    # doctor
    actor(d, 44, 600, "Doctor")
    d.line(62, 584, b - rx, 584, INK_2, 1.1)
    d.text(b, 620, "expiring link · no account", 9.5, 400, MUTED, "middle", italic=True)
    # admin + systems on the right
    actor(d, 568, 110, "Admin")
    for y in (52, 108, 276):
        d.line(552, 96, b + rx, y, INK_2, 1.1)
    for y, lbl in ((388, "LLM API"), (444, "TTS API")):
        d.rect(536, y - 20, 62, 40, fill=PAPER, stroke=EDGE["purple"], sw=1.3, rx=5)
        d.text(567, y - 5, "«system»", 9, 500, MUTED, "middle")
        d.text(567, y + 10, lbl, 10.5, 700, INK, "middle")
        d.line(536, y, b + rx, y, INK_2, 1.1)
    d.rect(110, 648, 404, 36, fill=PAPER, stroke=EDGE["red"], sw=1.1, rx=6)
    d.text(122, 670, "Out of scope: diagnosis · prescribing or dosing · emergency triage", 10.5, 600, TILE["red"])
    d.legend(96, 730, [("line", INK_2, "association"), ("dash", INK_2, "«include» / «extend»")])
    return d


# =============================================================================
# Activity diagram — portrait, two parts
# =============================================================================
LANES = [("User", "slate"), ("Web app", "cyan"), ("API", "blue"), ("Worker", "blue"), ("AI services", "purple")]


def _activity(height: int, spec, flows, extra) -> Diagram:
    d = page(PW, height)
    lw = (PW - 2) / 5
    cx = {}
    for i, (name, role) in enumerate(LANES):
        x = 1 + i * lw
        d.rect(x, 0, lw, height, fill=SNOW if i % 2 == 0 else PAPER, stroke=LINE, rx=0)
        d.rect(x, 0, lw, 24, fill=TILE[role], stroke="none", rx=0)
        d.text(x + lw / 2, 16, name, 11, 700, PAPER, "middle")
        cx[name.split()[0]] = x + lw / 2
    N = {}
    for key, kind, lane, y, rows, *opt in spec:
        x = cx[lane]
        if kind == "act":
            w, h = 108, 12 + 13.5 * len(rows)
            role = opt[0] if opt else "blue"
            dash = "4 3" if len(opt) > 1 and opt[1] else None
            d.rect(x - w / 2, y - h / 2, w, h, fill=PAPER, stroke=EDGE[role], sw=1.4, rx=10, dash=dash)
            d.lines(x, y - h / 2 + 16.5, rows, 10.5, 500, INK, "middle", 1.28)
            N[key] = (x, y, w / 2, h / 2)
        elif kind == "dec":
            d.raw(f'<path d="M{x},{y - 15} L{x + 15},{y} L{x},{y + 15} L{x - 15},{y} z" fill="{PAPER}" '
                  f'stroke="{INK_2}" stroke-width="1.4"/>')
            if rows:
                d.text(x + 20, y - 17, rows[0], 10, 500, INK_2)
            N[key] = (x, y, 15, 15)
        elif kind == "start":
            d.circle(x, y, 9, INK)
            N[key] = (x, y, 9, 9)
        elif kind == "end":
            d.circle(x, y, 10, PAPER, INK, 1.5)
            d.circle(x, y, 6, INK)
            N[key] = (x, y, 10, 10)
        elif kind == "conn":
            d.circle(x, y, 11, PAPER, INK, 1.5)
            d.text(x, y + 4, rows[0], 11, 700, INK, "middle")
            N[key] = (x, y, 11, 11)
    for a, b, label in flows:
        ax, ay, _, ah = N[a]
        bx, by, bw, bh = N[b]
        if abs(ax - bx) < 1:
            pts = [(ax, ay + ah), (bx, by - bh)]
        else:
            ex = bx - bw if bx > ax else bx + bw
            pts = [(ax, ay + ah), (ax, by), (ex, by)]
        d.arrow(pts, INK_2, sw=1.2)
        if label:
            d.text(ax + 6, ay + ah + 12, label, 9.5, 600, MUTED)
    extra(d, cx, N)
    return d


def activity_a() -> Diagram:
    spec = [
        ("s", "start", "User", 46, []),
        ("a1", "act", "User", 92, ["Photograph or", "choose the report"], "slate"),
        ("a2", "act", "Web", 160, ["Check type, size", "and image quality"], "cyan"),
        ("d1", "dec", "Web", 226, ["quality ok?"]),
        ("a2b", "act", "User", 226, ["Retake photo"], "slate"),
        ("a3", "act", "API", 296, ["Check consent", "store file", "create job"]),
        ("a4", "act", "Worker", 372, ["Claim job", "pre-process · OCR"]),
        ("a5", "act", "Worker", 438, ["Parse · map", "normalise · score"]),
        ("d2", "dec", "Worker", 502, ["row below τ?"]),
        ("a6", "act", "AI", 502, ["Local model", "structures rows"], "purple"),
        ("m1", "dec", "Worker", 562, []),
        ("a7", "act", "Web", 624, ["Show values", "beside the image"], "cyan"),
        ("a8", "act", "User", 690, ["Correct or", "confirm values"], "slate"),
        ("c", "conn", "User", 752, ["A"]),
    ]
    flows = [("s", "a1", None), ("a1", "a2", None), ("a2", "d1", None), ("d1", "a3", "[yes]"), ("a3", "a4", None),
             ("a4", "a5", None), ("a5", "d2", None), ("d2", "m1", "[no]"), ("m1", "a7", None), ("a7", "a8", None),
             ("a8", "c", None)]

    def extra(d, cx, N):
        x, y = N["d1"][:2]
        d.arrow([(x - 15, y), (cx["User"] + 54, y)], INK_2, sw=1.2)
        d.text(x - 20, y - 5, "[no]", 9.5, 600, MUTED, "end")
        d.arrow([(cx["User"] - 54, 226), (8, 226), (8, 92), (cx["User"] - 54, 92)], INK_2, sw=1.2)
        x, y = N["d2"][:2]
        d.arrow([(x + 15, y), (cx["AI"] - 54, y)], INK_2, sw=1.2)
        d.text(x + 20, y + 13, "[yes]", 9.5, 600, MUTED)
        d.arrow([(cx["AI"], y + 26), (cx["AI"], 562), (x + 15, 562)], INK_2, sw=1.2)
        d.text(cx["User"] + 16, 756, "continues in part (b)", 9.5, 500, MUTED)

    return _activity(776, spec, flows, extra)


def activity_b() -> Diagram:
    spec = [
        ("c", "conn", "User", 42, ["A"]),
        ("a9", "act", "Worker", 100, ["Classify · critical", "change · trend", "percentile"]),
        ("d3", "dec", "Worker", 176, ["critical?"]),
        ("a10", "act", "Web", 176, ["Show fixed", "urgent alert"], "red"),
        ("m2", "dec", "Worker", 240, []),
        ("a11", "act", "AI", 306, ["Retrieve passages", "write explanation"], "purple"),
        ("a12", "act", "Worker", 376, ["Safety validation", "(template on fail)"]),
        ("a13", "act", "AI", 444, ["Narrate", "(if voice is on)"], "purple", True),
        ("a14", "act", "Web", 512, ["Render body map", "trends · text"], "cyan"),
        ("a15", "act", "User", 580, ["Explore · listen", "share · export"], "slate"),
        ("e", "end", "User", 636, []),
    ]
    flows = [("c", "a9", None), ("a9", "d3", None), ("d3", "m2", "[no]"), ("m2", "a11", None), ("a11", "a12", None),
             ("a12", "a13", None), ("a13", "a14", None), ("a14", "a15", None), ("a15", "e", None)]

    def extra(d, cx, N):
        x, y = N["d3"][:2]
        d.arrow([(x - 15, y), (cx["Web"] + 54, y)], INK_2, sw=1.2)
        d.text(x - 20, y - 5, "[yes]", 9.5, 600, MUTED, "end")
        d.arrow([(cx["Web"], y + 26), (cx["Web"], 240), (x - 15, 240)], INK_2, sw=1.2)

    return _activity(656, spec, flows, extra)


# =============================================================================
# Sequence diagram — portrait, two parts
# =============================================================================
def _sequence(parts: list[tuple[str, str]], msgs: list, x0: float, gap: float) -> Diagram:
    step = 30
    h = 50 + sum({"frame-": 10, "frame+": 24}.get(m[0], step) for m in msgs) + 20
    d = page(PW, int(h))
    X = {name: x0 + i * gap for i, (name, _) in enumerate(parts)}
    hw = min(gap - 8, 96)
    for name, role in parts:
        x = X[name]
        d.rect(x - hw / 2, 2, hw, 28, fill=PAPER, stroke=EDGE[role], sw=1.4, rx=5)
        d.rect(x - hw / 2, 2, hw, 4, fill=TILE[role], stroke="none", rx=2)
        d.text(x, 22, name, 10.5, 700, INK, "middle")
        d.line(x, 30, x, h - 6, "#B8C0CE", 1.1, "4 4")
    y, n, frames = 58, 0, []
    for m in msgs:
        if m[0] == "frame+":
            _, kind, cond, p1, p2 = m
            frames.append((kind, cond, X[p1] - 40, min(X[p2] + 40, PW - 3), y - 16))
            y += 24
            continue
        if m[0] == "frame-":
            kind, cond, x1, x2, fy = frames.pop()
            d.rect(x1, fy, x2 - x1, y - fy - 6, fill="none", stroke=INK_2, sw=1, rx=2)
            w = text_width(kind, 10, 700) + 14
            d.raw(f'<path d="M{x1},{fy} h{w} v10 l-5,5 h-{w - 5} z" fill="{SNOW_2}" stroke="{INK_2}" stroke-width="1"/>')
            d.text(x1 + 6, fy + 11, kind, 10, 700, INK)
            d.text(x1 + w + 6, fy + 11, cond, 10, 500, INK_2)
            y += 10
            continue
        src, dst, label = m[0], m[1], m[2]
        reply = len(m) > 3
        n += 1
        x1, x2 = X[src], X[dst]
        color = TILE["orange"] if {"LLM API", "TTS API"} & {src, dst} else INK_2
        if src == dst:
            d.arrow([(x1, y - 6), (x1 + 26, y - 6), (x1 + 26, y + 8), (x1 + 3, y + 8)], color, sw=1.2)
            d.text(x1 + 32, y + 5, label, 10, 400, INK)
            d.circle(x1 - 11, y + 1, 7, SNOW_2)
            d.text(x1 - 11, y + 4.5, str(n), 8.5, 700, INK_2, "middle")
        else:
            d.arrow([(x1, y), (x2 + (-3 if x2 > x1 else 3), y)], color, sw=1.2,
                    dash="5 3" if reply else None, head="open" if reply else "arrow")
            left = min(x1, x2)
            d.circle(left + 11, y - 10, 7, SNOW_2)
            d.text(left + 11, y - 6.5, str(n), 8.5, 700, INK_2, "middle")
            d.text(left + 22, y - 6, label, 10, 400, INK)
        y += step
    return d


def sequence_a() -> Diagram:
    parts = [("User", "slate"), ("Web app", "cyan"), ("API", "blue"), ("PostgreSQL", "green"), ("Worker", "blue"),
             ("Local LLM", "purple")]
    msgs = [
        ("User", "Web app", "choose photo / PDF"),
        ("Web app", "Web app", "quality check"),
        ("Web app", "API", "POST /reports"),
        ("API", "PostgreSQL", "INSERT report + job"),
        ("API", "Web app", "202 Accepted", "r"),
        ("Worker", "PostgreSQL", "claim job (SKIP LOCKED)"),
        ("Worker", "Worker", "pre-process · OCR"),
        ("Worker", "Worker", "parse · map · score"),
        ("frame+", "alt", "[confidence < τ]", "Worker", "Local LLM"),
        ("Worker", "Local LLM", "structure rows"),
        ("Local LLM", "Worker", "rows JSON", "r"),
        ("frame-",),
        ("Worker", "PostgreSQL", "INSERT observations"),
        ("Web app", "API", "GET status (SSE)"),
        ("API", "Web app", "draft values", "r"),
        ("Web app", "User", "review screen", "r"),
    ]
    return _sequence(parts, msgs, 50, 100)


def sequence_b() -> Diagram:
    parts = [("User", "slate"), ("Web app", "cyan"), ("API", "blue"), ("PostgreSQL", "green"), ("Worker", "blue"),
             ("LLM API", "orange"), ("TTS API", "orange")]
    msgs = [
        ("User", "Web app", "confirm values"),
        ("Web app", "API", "POST /confirm"),
        ("API", "PostgreSQL", "mark verified · enqueue"),
        ("Worker", "PostgreSQL", "load history"),
        ("Worker", "Worker", "ranges · critical · trend"),
        ("Worker", "PostgreSQL", "kNN passages"),
        ("Worker", "LLM API", "de-identified values"),
        ("LLM API", "Worker", "explanation JSON", "r"),
        ("Worker", "Worker", "safety validation"),
        ("frame+", "opt", "[voice on]", "Worker", "TTS API"),
        ("Worker", "TTS API", "text + language"),
        ("TTS API", "Worker", "audio", "r"),
        ("frame-",),
        ("Worker", "PostgreSQL", "save explanation"),
        ("Web app", "API", "GET /insights"),
        ("API", "Web app", "organs · trends · text", "r"),
        ("Web app", "User", "3D body map", "r"),
    ]
    return _sequence(parts, msgs, 44, 85.5)


# =============================================================================
# State machine — portrait (vertical)
# =============================================================================
def state_machine() -> Diagram:
    d = page(PW, 810)

    def st(x, y, name, code, role="blue", w=150):
        d.rect(x - w / 2, y - 21, w, 42, fill=PAPER, stroke=EDGE[role], sw=1.5, rx=13)
        d.text(x, y - 2, name, 11.5, 650, INK, "middle")
        d.text(x, y + 13, code, 9.5, 400, MUTED, "middle", family=MONO)

    def lab(x, y, s, color=INK_2, anchor="start"):
        d.text(x, y, s, 10, 500, color, anchor)

    X = 300
    d.circle(X, 14, 8, INK)
    st(X, 60, "Uploaded", "uploaded", "slate")
    st(X, 140, "Queued", "queued")
    d.rect(150, 184, 300, 94, fill=SNOW, stroke=TILE["blue"], sw=1.4, rx=14)
    d.text(164, 202, "Processing", 11.5, 700, INK)
    d.text(236, 202, "processing", 9.5, 400, MUTED, family=MONO)
    for i, s in enumerate(["Pre-process", "OCR", "Parse & map"]):
        bx = 176 + i * 96
        d.rect(bx, 222, 82, 34, fill=PAPER, stroke=EDGE["blue"], sw=1.3, rx=10)
        d.text(bx + 41, 243, s, 10.5, 600, INK, "middle")
        if i < 2:
            d.arrow([(bx + 83, 239), (bx + 95, 239)], INK_2, sw=1.1)
    st(X, 330, "Needs review", "needs_review", "orange")
    st(X, 410, "Verified", "verified", "green")
    st(X, 490, "Analysing", "analysing")
    st(X, 570, "Explaining", "explaining", "purple")
    st(X, 650, "Explained", "explained", "green")
    st(96, 60, "Rejected", "rejected", "red", 130)
    st(510, 570, "Failed", "failed", "red", 130)
    st(96, 740, "Deleted", "deleted", "slate", 130)
    d.circle(300, 740, 10, PAPER, INK, 1.5)
    d.circle(300, 740, 6, INK)

    a = dict(color=INK_2, sw=1.3)
    d.arrow([(X, 22), (X, 39)], **a)
    d.arrow([(X, 81), (X, 119)], **a); lab(X + 8, 104, "consent ok")
    d.arrow([(X, 161), (X, 184)], **a); lab(X + 8, 177, "claimed")
    d.arrow([(X, 278), (X, 309)], **a); lab(X + 8, 297, "draft saved")
    d.arrow([(X, 351), (X, 389)], **a); lab(X + 8, 374, "user confirms")
    d.arrow([(X, 431), (X, 469)], **a); lab(X + 8, 454, "enqueue")
    d.arrow([(X, 511), (X, 549)], **a); lab(X + 8, 534, "analysed")
    d.arrow([(X, 591), (X, 629)], **a); lab(X + 8, 614, "validated")
    d.arrow([(X - 75, 60), (161, 60)], **a); lab(X - 80, 50, "invalid / no consent", anchor="end")
    d.arrow([(96, 81), (96, 719)], **a)
    d.arrow([(X - 75, 650), (120, 650), (120, 719)], **a); lab(128, 640, "user deletes")
    d.arrow([(161, 740), (290, 740)], **a); lab(172, 732, "30-day purge")
    d.arrow([(450, 262), (474, 262), (474, 140), (X + 75, 140)], color=INK_2, sw=1.2, dash="5 4")
    lab(482, 196, "error, < 3 tries")
    lab(482, 210, "→ retry")
    d.arrow([(450, 240), (536, 240), (536, 549)], color=RED, sw=1.3)
    lab(544, 300, "3rd failure", RED)
    d.arrow([(X + 75, 570), (445, 570)], color=RED, sw=1.3); lab(X + 82, 562, "retries out", RED)
    d.arrow([(510, 591), (510, 620), (560, 620), (560, 330), (X + 75, 330)], color=INK_2, sw=1.2, dash="5 4")
    lab(566, 470, "admin")
    lab(566, 484, "retry")
    d.arrow([(X + 75, 650), (410, 650), (410, 410), (X + 75, 410)], color=INK_2, sw=1.2)
    lab(418, 540, "edit a value")
    lab(418, 554, "→ re-analyse")
    d.text(300, 790, "Delete is allowed from every state; only an audit entry remains.", 10, 500, MUTED, "middle",
           italic=True)
    return d


# =============================================================================
# ER diagram — portrait, two parts (with columns)
# =============================================================================
def _er(height: int, place: dict, rels: list, notes: list[str]) -> Diagram:
    d = page(PW, height)
    W, HEAD, ROW = 164, 22, 14
    box = {}
    for name, (x, y) in place.items():
        role, cols = ENTITIES[name]
        h = HEAD + len(cols) * ROW + 6
        box[name] = (x, y, h)
        d.rect(x, y, W, h, fill=PAPER, stroke=EDGE[role], sw=1.3, rx=4)
        d.rect(x, y, W, HEAD, fill=TILE[role], stroke="none", rx=4)
        d.rect(x, y + HEAD - 4, W, 4, fill=TILE[role], stroke="none", rx=0)
        d.text(x + 8, y + 15.5, name, 10.5, 700, PAPER, family=MONO)
        for i, (k, col, typ) in enumerate(cols):
            ry = y + HEAD + 3 + i * ROW
            kc = {"PK": TILE["orange"], "FK": TILE["blue"], "UQ": TILE["green"]}.get(k, MUTED)
            d.text(x + 6, ry + 10.5, k, 8, 700, kc, family=MONO)
            d.text(x + 26, ry + 10.5, col, 9.5, 600 if k == "PK" else 400, INK, family=MONO)
            d.text(x + W - 6, ry + 10.5, typ, 8.5, 400, MUTED, "end", family=MONO)

    def ry(ent, col):
        x, y, _ = box[ent]
        i = [c for _, c, _ in ENTITIES[ent][1]].index(col)
        return y + HEAD + 3 + i * ROW + ROW / 2

    def pt(ent, side, col=None):
        x, y, h = box[ent]
        return {"L": (x, ry(ent, col) if col else y + h / 2), "R": (x + W, ry(ent, col) if col else y + h / 2),
                "T": (x + W / 2, y), "B": (x + W / 2, y + h)}[side]

    def end(p, q, kind):
        (x1, y1), (x2, y2) = p, q
        ux, uy = x2 - x1, y2 - y1
        ln = (ux * ux + uy * uy) ** 0.5
        ux, uy = ux / ln, uy / ln
        px, py = -uy, ux
        parts = []

        def tick(t):
            cx, cy = x1 + ux * t, y1 + uy * t
            parts.append(f"M{cx + px * 5:.1f},{cy + py * 5:.1f} L{cx - px * 5:.1f},{cy - py * 5:.1f}")

        if kind in ("one", "one_many"):
            tick(10)
        if kind == "one":
            tick(14)
        if kind in ("one_many", "zero_many"):
            parts.append(f"M{x1 + px * 6:.1f},{y1 + py * 6:.1f} L{x1 + ux * 9:.1f},{y1 + uy * 9:.1f} "
                         f"L{x1 - px * 6:.1f},{y1 - py * 6:.1f}")
        if kind == "zero_one":
            tick(9)
        d.raw(f'<path d="{" ".join(parts)}" stroke="{INK_2}" stroke-width="1.2" fill="none"/>')
        if kind in ("zero_many", "zero_one"):
            t = 17 if kind == "zero_many" else 16
            d.circle(x1 + ux * t, y1 + uy * t, 3.6, PAPER, INK_2, 1.2)

    for (e1, s1, c1), (e2, s2, c2), k1, k2, via in rels:
        p1, p2 = pt(e1, s1, c1), pt(e2, s2, c2)
        if via is None:
            pts = [p1, p2]
        else:
            pts = [p1, (via, p1[1]), (via, p2[1]), p2]
        d.arrow(pts, INK_2, sw=1.15, head=None)
        end(pts[0], pts[1], k1)
        end(pts[-1], pts[-2], k2)
    y = height - 12 - 14 * (len(notes) - 1)
    for i, s in enumerate(notes):
        d.text(20, y + i * 14, s, 9.5, 400, MUTED)
    return d


C0, C1, C2 = 20, 226, 432


def er_a() -> Diagram:
    place = {"app_user": (C0, 6), "consent": (C0, 186), "audit_log": (C0, 350), "share_link": (C0, 514),
             "profile": (C1, 6), "report": (C1, 186), "report_file": (C1, 376), "report_page": (C1, 540),
             "processing_job": (C2, 6), "observation": (C2, 186)}
    rels = [
        (("app_user", "R", "id"), ("profile", "L", "owner_user_id"), "one", "zero_many", 205),
        (("app_user", "B", None), ("consent", "T", None), "one", "zero_many", None),
        (("consent", "R", "profile_id"), ("profile", "L", "deleted_at"), "zero_many", "one", 212),
        (("app_user", "R", "role"), ("audit_log", "R", "actor_user_id"), "zero_one", "zero_many", 198),
        (("profile", "B", None), ("report", "T", None), "one", "zero_many", None),
        (("report", "B", None), ("report_file", "T", None), "one", "one_many", None),
        (("report_file", "B", None), ("report_page", "T", None), "one", "one_many", None),
        (("report", "R", "id"), ("processing_job", "L", "report_id"), "one", "zero_many", 411),
        (("report", "R", "lab_name"), ("observation", "L", "report_id"), "one", "zero_many", 418),
        (("report_page", "R", "id"), ("observation", "L", "report_page_id"), "zero_one", "zero_many", 404),
        (("share_link", "R", "report_id"), ("report", "L", "deleted_at"), "zero_many", "one", 206),
    ]
    return _er(700, place, rels, [
        "observation.test_id → lab_test and profile → trend_insight are shown in part (b).",
    ])


def er_b() -> Diagram:
    place = {"explanation": (C0, 6), "explanation_citation": (C0, 196), "feedback": (C0, 296),
             "trend_insight": (C0, 440),
             "organ_system": (C1, 6), "lab_test": (C1, 146), "kb_chunk": (C1, 356), "kb_document": (C1, 520),
             "unit_conversion": (C2, 6), "reference_range": (C2, 146), "critical_limit": (C2, 318),
             "population_percentile": (C2, 462)}
    rels = [
        (("organ_system", "B", None), ("lab_test", "T", None), "one", "zero_many", None),
        (("lab_test", "R", "id"), ("unit_conversion", "L", "test_id"), "one", "zero_many", 411),
        (("lab_test", "R", "id"), ("reference_range", "L", "test_id"), "one", "zero_many", 411),
        (("lab_test", "R", "id"), ("critical_limit", "L", "test_id"), "one", "zero_many", 411),
        (("lab_test", "R", "id"), ("population_percentile", "L", "test_id"), "one", "zero_many", 411),
        (("lab_test", "B", None), ("kb_chunk", "T", None), "zero_one", "zero_many", None),
        (("kb_document", "T", None), ("kb_chunk", "B", None), "one", "one_many", None),
        (("explanation", "B", None), ("explanation_citation", "T", None), "one", "zero_many", None),
        (("kb_chunk", "L", "id"), ("explanation_citation", "R", "kb_chunk_id"), "one", "zero_many", 205),
        (("explanation", "R", "language"), ("feedback", "R", "explanation_id"), "one", "zero_many", 196),
        (("lab_test", "L", "id"), ("trend_insight", "R", "test_id"), "one", "zero_many", 213),
    ]
    return _er(700, place, rels, [
        "explanation.report_id → report, trend_insight.profile_id → profile and feedback.user_id → app_user",
        "are shown in part (a). Legend: PK primary key · FK foreign key · UQ unique.",
    ])


# =============================================================================
# Class diagrams — portrait, two parts
# =============================================================================
def _cls(d, x, y, w, name, attrs, methods, role, stereo=None) -> tuple[float, float, float, float]:
    hh = 36 if stereo else 24
    h = hh + (len(attrs) * 13 + 8 if attrs else 6) + len(methods) * 13 + 8
    d.rect(x, y, w, h, fill=PAPER, stroke=EDGE[role], sw=1.3, rx=3)
    d.rect(x, y, w, hh, fill=EDGE[role], stroke="none", rx=3, opacity=0.2)
    d.rect(x, y, w, 3, fill=TILE[role], stroke="none", rx=1.5)
    if stereo:
        d.text(x + w / 2, y + 15, f"«{stereo}»", 9, 500, MUTED, "middle")
        d.text(x + w / 2, y + 29, name, 11, 700, INK, "middle", italic=stereo == "interface")
    else:
        d.text(x + w / 2, y + 17, name, 11, 700, INK, "middle")
    yy = y + hh
    d.line(x, yy, x + w, yy, EDGE[role], 1)
    for i, a in enumerate(attrs):
        d.text(x + 7, yy + 13 + i * 13, a, 9.5, 400, INK_2, family=MONO)
    yy += len(attrs) * 13 + 8 if attrs else 6
    d.line(x, yy, x + w, yy, EDGE[role], 1)
    for i, m in enumerate(methods):
        d.text(x + 7, yy + 13 + i * 13, m, 9.5, 400, INK, family=MONO)
    return (x, y, w, h)


def class_a() -> Diagram:
    d = page(PW, 520)
    W = 180
    X = [8, 211, 414]
    B = {}
    B["router"] = _cls(d, X[0], 6, W, "ReportsRouter", ["- service"], ["+ upload(profile, file)", "+ confirm(id, edits)",
                                                                       "+ insights(id)"], "cyan", "FastAPI router")
    B["service"] = _cls(d, X[1], 6, W, "ReportService", ["- repo", "- storage", "- queue"],
                        ["+ create(): Report", "+ confirm(): Report", "+ delete(): None"], "blue")
    B["repo"] = _cls(d, X[2], 6, W, "ReportRepository", ["- session"], ["+ get(id): Report", "+ save(report)",
                                                                         "+ history(profile, test)"], "blue")
    B["storage"] = _cls(d, X[0], 200, W, "StorageBackend", [], ["+ put(key, data)", "+ get(key): bytes",
                                                                 "+ delete(key)"], "green", "interface")
    B["queue"] = _cls(d, X[1], 200, W, "JobQueue", [], ["+ enqueue(id, stage)", "+ claim(): Job | None",
                                                        "+ fail(job, error)"], "green", "interface")
    B["worker"] = _cls(d, X[2], 200, W, "Worker", ["- queue", "- handlers"], ["+ run_forever()", "+ process(job)"],
                       "slate")
    B["local"] = _cls(d, X[0], 372, W, "LocalVolumeStorage", ["- root: Path"], ["+ put / get / delete"], "green")
    B["pgq"] = _cls(d, X[1], 372, W, "PgJobQueue", ["- engine"], ["+ claim(): SKIP LOCKED"], "green")
    B["handler"] = _cls(d, X[2], 372, W, "StageHandler", ["+ stage: Stage"], ["+ handle(job)"], "slate", "interface")

    def L(k, f=0.5):
        x, y, w, h = B[k]; return (x, y + h * f)

    def R(k, f=0.5):
        x, y, w, h = B[k]; return (x + w, y + h * f)

    def T(k, f=0.5):
        x, y, w, h = B[k]; return (x + w * f, y)

    def Bo(k, f=0.5):
        x, y, w, h = B[k]; return (x + w * f, y + h)

    assoc = dict(color=INK_2, sw=1.2, head="open")
    real = dict(color=INK_2, sw=1.1, head="triangle", dash="5 3")
    d.arrow([R("router", 0.4), L("service", 0.4)], **assoc)
    d.arrow([R("service", 0.4), L("repo", 0.4)], **assoc)
    d.arrow([Bo("service", 0.5), T("queue", 0.5)], **assoc)
    sb = Bo("service", 0.2)
    d.arrow([sb, (sb[0], sb[1] + 14), (T("storage")[0], sb[1] + 14), T("storage")], **assoc)
    d.arrow([L("worker", 0.4), R("queue", 0.4)], **assoc)
    d.arrow([Bo("worker"), T("handler")], color=INK_2, sw=1.2, head="open", tail="diamond")
    d.text(Bo("worker")[0] + 8, (Bo("worker")[1] + T("handler")[1]) / 2 + 4, "1..*", 9.5, 600, MUTED)
    d.arrow([T("local"), Bo("storage")], **real)
    d.arrow([T("pgq"), Bo("queue")], **real)
    d.legend(8, 500, [("line", INK_2, "association"), ("dash", INK_2, "realisation")])
    d.raw(f'<path d="M300,500 h22" stroke="{INK_2}" stroke-width="1.2" '
          f'marker-start="url(#{d._marker(INK_2, "diamond")})"/>')
    d.text(330, 504, "composition", 11, 400, INK_2)
    return d


def class_b() -> Diagram:
    d = page(PW, 640)
    pw, pad = 144, 6
    W = pw - 2 * pad
    xs = [3, 153, 303, 453]
    B = {}
    B["handler"] = _cls(d, 226, 4, 150, "StageHandler", [], ["+ handle(job)"], "slate", "interface")
    pk = [
        ("extraction", "teal", [
            ("extract", "ExtractionStage", [], ["+ handle(job)"], "slate", None),
            ("ocr", "OCREngine", [], ["+ read(image)"], "teal", "interface"),
            ("paddle", "RapidOCREngine", [], ["+ read(image)"], "teal", None),
            ("matcher", "CatalogMatcher", [], ["+ match(row)"], "teal", None),
            ("conf", "ConfidenceModel", [], ["+ score(features)"], "teal", None),
        ]),
        ("analysis", "cyan", [
            ("analyse", "AnalysisStage", [], ["+ handle(job)"], "slate", None),
            ("change", "ChangeDetector", [], ["+ significant(a, b)"], "cyan", None),
            ("trend", "TrendAnalyzer", [], ["+ slope(series)"], "cyan", None),
            ("critical", "CriticalRules", [], ["+ check(obs)"], "red", None),
        ]),
        ("explanation", "purple", [
            ("explain", "ExplanationStage", [], ["+ handle(job)"], "slate", None),
            ("retriever", "KnowledgeRetriever", [], ["+ top_k(tests, k)"], "purple", None),
            ("validator", "SafetyValidator", [], ["+ validate(text)"], "red", None),
            ("llm", "LLMProvider", [], ["+ complete(prompt)"], "purple", "interface"),
            ("anthropic", "GroqProvider", [], ["+ complete(prompt)"], "purple", None),
            ("ollama", "OllamaProvider", [], ["+ complete(prompt)"], "purple", None),
        ]),
        ("narration", "orange", [
            ("narrate", "NarrationStage", [], ["+ handle(job)"], "slate", None),
            ("tts", "TTSProvider", [], ["+ speak(text, lang)"], "orange", "interface"),
        ]),
    ]
    top = 96
    for (pname, role, classes), x in zip(pk, xs):
        d.rect(x, top, pw, 530, fill=EDGE[role], stroke=EDGE[role], sw=1.2, rx=4, opacity=0.07)
        d.rect(x, top - 16, text_width(pname, 10.5, 700) + 16, 16, fill=TILE[role], stroke="none", rx=2)
        d.text(x + 8, top - 4, pname, 10.5, 700, PAPER)
        y = top + 12
        for key, name, attrs, methods, crole, stereo in classes:
            B[key] = _cls(d, x + pad, y, W, name, attrs, methods, crole, stereo)
            y += B[key][3] + 26
    real = dict(color=INK_2, sw=1.1, head="triangle", dash="5 3")
    use = dict(color=INK_2, sw=1.1, head="open", dash="4 3")
    hx, hy, hw, hh = B["handler"]
    bus = hy + hh + 22
    for k in ("extract", "analyse", "explain", "narrate"):
        x, y, w, h = B[k]
        d.arrow([(x + w / 2, y), (x + w / 2, bus)], color=INK_2, sw=1.1, head=None, dash="5 3")
    d.arrow([(B["extract"][0] + W / 2, bus), (B["narrate"][0] + W / 2, bus)], color=INK_2, sw=1.1, head=None, dash="5 3")
    d.arrow([(hx + hw / 2, bus), (hx + hw / 2, hy + hh)], **real)
    # uses: stage → first collaborator; implementations → interfaces
    for s, c in (("extract", "ocr"), ("analyse", "change"), ("explain", "retriever"), ("narrate", "tts")):
        x, y, w, h = B[s]
        d.arrow([(x + w / 2, y + h), (x + w / 2, B[c][1])], **use)
    for impl, iface in (("paddle", "ocr"), ("anthropic", "llm")):
        x, y, w, h = B[impl]
        d.arrow([(x + w / 2, y), (x + w / 2, B[iface][1] + B[iface][3])], **real)
    ox, oy, ow, oh = B["ollama"]
    lx, ly, lw_, lh = B["llm"]
    d.arrow([(ox + ow, oy + oh / 2), (ox + ow + 5, oy + oh / 2), (ox + ow + 5, ly + lh / 2), (lx + lw_, ly + lh / 2)],
            **real)
    d.text(3, 636, "Each stage uses the classes in its package; dashed triangles mark implementations.",
           9.5, 400, MUTED)
    return d


# =============================================================================
# Gantt — landscape
# =============================================================================
def gantt() -> Diagram:
    rows = list(csv.DictReader((SRC / "schedule.csv").open(encoding="utf-8")))
    for r in rows:
        r["s"], r["e"] = date.fromisoformat(r["start"]), date.fromisoformat(r["end"])
    start, end = min(r["s"] for r in rows), max(r["e"] for r in rows)
    days = (end - start).days + 1
    x0, x1, rh, top = 356, LW - 4, 15.5, 40
    px = (x1 - x0) / days
    H = int(top + len(rows) * rh + 34)
    d = page(LW, H)
    X = lambda dt: x0 + (dt - start).days * px  # noqa: E731
    d.rect(0, 0, LW, top - 4, fill=SNOW, stroke="none", rx=3)
    d.text(6, 22, "ID", 9.5, 700, MUTED)
    d.text(40, 22, "Task", 9.5, 700, MUTED)
    d.text(318, 22, "Owner", 9.5, 700, MUTED)
    month = None
    for i in range(days):
        dt = start + timedelta(days=i)
        if dt.weekday() >= 5:
            d.rect(X(dt), top, px, len(rows) * rh, fill=SNOW, stroke="none", rx=0)
        if dt.month != month:
            month = dt.month
            d.text(X(dt) + 3, 13, f"{dt:%b}", 10, 700, INK)
        if dt.weekday() == 0:
            d.line(X(dt), 18, X(dt), top + len(rows) * rh, LINE, 0.8)
            d.text(X(dt) + 3, 31, f"{dt:%d}", 9.5, 500, INK_2)
    for i, r in enumerate(rows):
        y = top + i * rh
        if r["kind"] == "phase":
            d.rect(0, y, LW, rh, fill=SNOW_2, stroke="none", rx=0, opacity=0.8)
            d.text(6, y + 11.5, r["id"], 9.5, 700, INK, family=MONO)
            d.text(40, y + 11.5, r["phase"], 10.5, 700, INK)
            xs, xe = X(r["s"]), X(r["e"]) + px
            d.raw(f'<path d="M{xs:.1f},{y + 12} V{y + 5} H{xe:.1f} V{y + 12}" fill="none" stroke="{INK}" stroke-width="2.4"/>')
            continue
        d.text(6, y + 11.5, r["id"], 9.5, 500, MUTED, family=MONO)
        task = r["task"] if text_width(r["task"], 10) < 272 else r["task"][:46] + "…"
        d.text(40, y + 11.5, task, 10, 600 if r["kind"] == "milestone" else 400, INK)
        role = OWNER[r["owner"]][0]
        if r["kind"] == "milestone":
            cx = X(r["e"]) + px / 2
            d.raw(f'<path d="M{cx},{y + 2} l6,6 -6,6 -6,-6 z" fill="{TILE["orange"]}"/>')
            d.text(cx + 9, y + 11.5, f"{r['e']:%d %b}", 9.5, 700, TILE["orange"])
            d.text(318, y + 11.5, "gate", 9.5, 700, TILE["orange"])
            continue
        d.text(318, y + 11.5, r["owner"], 9, 700, TILE[role])
        xs, xe = X(r["s"]), X(r["e"]) + px
        if r["kind"] == "buffer":
            d.rect(xs, y + 3.5, xe - xs, 9, fill=PAPER, stroke=MUTED, sw=0.9, rx=3, dash="2 2")
        else:
            d.rect(xs, y + 3.5, xe - xs, 9, fill=TILE[role], stroke="none", rx=3)
    ly = top + len(rows) * rh + 20
    d.legend(6, ly, [("box", TILE["blue"], "Developer"), ("box", TILE["purple"], "Team members"),
                     ("box", TILE["green"], "Whole team"), ("box", SNOW, "weekend")])
    d.raw(f'<path d="M520,{ly - 6} l6,6 -6,6 -6,-6 z" fill="{TILE["orange"]}"/>')
    d.text(532, ly + 4, "milestone / gate", 11, 400, INK_2)
    return d


# =============================================================================
# Life cycle — portrait
# =============================================================================
def lifecycle() -> Diagram:
    d = page(PW, 520)
    phases = [
        ("Inception", "1 – 9 Aug", "slate", ["Problem & persona validation", "Charter, SRS, architecture",
                                                  "Risk register, test plan", "Repo + Docker scaffold"], "M0 · docs baseline"),
        ("Elaboration", "10 – 16 Aug", "cyan", ["Test catalogue (60 tests)", "Synthetic report generator",
                                               "3D anatomy spike", "Knowledge sources + licences"], "risks retired"),
        ("Construction", "17 Aug – 20 Sep", "blue", ["S2–S3 extraction + review", "S4 analytics engine",
                                                      "S5 grounded explanations", "S6 body map + accounts"],
         "M1 30 Aug · M2 20 Sep"),
        ("Transition", "21 – 30 Sep", "green", ["S7 evaluation + hardening", "User tests + doctor review",
                                                    "Report, poster, rehearsal", "Offline demo mode"], "M3 · demo ready"),
    ]
    w, tip = 142, 10
    for i, (name, when, role, acts, gate) in enumerate(phases):
        x = 2 + i * 150
        pts = f"{x},2 {x + w},2 {x + w + tip},24 {x + w},46 {x},46"
        if i:
            pts += f" {x + tip},24"
        d.raw(f'<polygon points="{pts}" fill="{TILE[role]}"/>')
        d.text(x + (18 if i else 10), 21, name, 12, 700, PAPER)
        d.text(x + (18 if i else 10), 37, when, 9.5, 500, PAPER)
        d.rect(x, 56, w, 158, fill=PAPER, stroke=LINE, rx=6)
        yy = 76
        for a in acts:
            wrapped = _wrap(a, 22)
            d.circle(x + 11, yy - 3.5, 2.8, TILE[role])
            yy = d.lines(x + 19, yy, wrapped, 10, 400, INK, leading=1.3) + 8
        d.raw(f'<path d="M{x + 12},{226} l8,8 -8,8 -8,-8 z" fill="{TILE["orange"]}"/>')
        d.text(x + 26, 238, gate, 10, 650, INK)
    d.rect(0, 262, PW, 250, fill=SNOW, stroke="none", rx=8)
    d.text(12, 284, "Inside every construction sprint (one week)", 11.5, 700, INK)
    steps = [("Plan", "Mon", "calendar", ["pick backlog items;", "define done"]),
             ("Build", "Mon–Thu", "api", ["feature branch,", "tests first"]),
             ("Verify", "Thu–Fri", "check", ["unit + integration", "tests, eval runs"]),
             ("Review", "Sat", "users", ["team demo; guide", "every 2nd week"]),
             ("Retro", "Sun", "chart", ["update risks,", "docs and Gantt"])]
    for i, (nm, when, gl, rows) in enumerate(steps):
        x = 10 + i * 118
        d.rect(x, 298, 104, 150, fill=PAPER, stroke=LINE, rx=6)
        d.rect(x + 10, 310, 28, 28, fill=TILE["blue"], stroke="none", rx=6)
        d.raw(icon(gl, x + 16, 316, 16))
        d.text(x + 10, 360, nm, 12, 700, INK)
        d.text(x + 10, 376, when, 10, 500, MUTED)
        d.lines(x + 10, 400, rows, 10, 400, INK_2)
        if i < 4:
            d.arrow([(x + 105, 373), (x + 117, 373)], INK_2, sw=1.2)
    d.arrow([(10 + 4 * 118 + 52, 449), (10 + 4 * 118 + 52, 478), (62, 478), (62, 449)], INK_2, dash="5 4")
    d.pill(300, 478, "repeat for sprints 2 – 7", INK_2, 10)
    return d


# =============================================================================
# User journey — landscape
# =============================================================================
def journey() -> Diagram:
    d = page(LW, 450)
    stages = ["Report arrives", "Upload", "Check values", "Understand", "Act", "Track"]
    x0, cw = 170, 126
    d.rect(0, 0, 158, 440, fill=SNOW, stroke="none", rx=8)
    d.rect(12, 12, 36, 36, fill=TILE["slate"], stroke="none", rx=18)
    d.raw(icon("user", 20, 20, 20))
    y = 68
    for head, body in [("Priya · caregiver", ["Engineer in Bengaluru;", "father prefers Odia."]),
                       ("Goal", ["Know if anything needs", "a doctor, before the", "next visit."]),
                       ("Frustration", ["Dense tables; web", "searches are slow", "and frightening."]),
                       ("Ramesh · patient", ["58, borderline sugar,", "yearly check-up."])]:
        d.text(12, y, head, 11, 700, INK)
        y = d.lines(12, y + 16, body, 10, 400, INK_2) + 12
    rows = {
        "Doing": (48, 62, [["PDF arrives on", "WhatsApp"], ["Shares the PDF", "to Nabz"], ["Fixes one OCR", "error"],
                           ["Taps glowing liver;", "plays Odia audio"], ["Books follow-up;", "shares summary"],
                           ["Scrubs the", "timeline"]]),
        "Pain points": (262, 54, [["20+ unfamiliar", "abbreviations"], ["skewed, shadowed", "photos"],
                                  ["OCR errors would", "mislead"], ["alarming, generic", "search results"],
                                  ["5-minute visit;", "forgets questions"], ["different labs,", "different units"]]),
        "How Nabz helps": (324, 54, [["body map shows", "what matters"], ["quality check", "+ retake tips"],
                                     ["human review of", "weak rows"], ["grounded, cited,", "in Odia"],
                                     ["doctor questions", "+ share link"], ["trends + change", "significance"]]),
    }
    for i, s in enumerate(stages):
        x = x0 + i * cw
        d.rect(x, 8, cw - 6, 30, fill=TILE["blue"], stroke="none", rx=5)
        d.text(x + (cw - 6) / 2, 28, f"{i + 1} · {s}", 11, 700, PAPER, "middle")
    for label, (y, h, cells) in rows.items():
        for i, lines_ in enumerate(cells):
            x = x0 + i * cw
            if label == "Doing":
                d.rect(x, y, cw - 6, h, fill=PAPER, stroke=LINE, rx=6)
            elif label == "Pain points":
                d.rect(x, y, cw - 6, h, fill=PAPER, stroke=EDGE["red"], sw=1, rx=6)
            else:
                d.rect(x, y, cw - 6, h, fill=EDGE["green"], stroke="none", rx=6, opacity=0.2)
            d.lines(x + 9, y + 20, lines_, 10, 600 if label == "How Nabz helps" else 400, INK, leading=1.35)
    # feeling curve
    fy, fh = 118, 134
    d.rect(x0, fy, 6 * cw - 6, fh, fill=PAPER, stroke=LINE, rx=6)
    base, amp = fy + fh / 2 + 4, 42
    d.line(x0 + 8, base, x0 + 6 * cw - 14, base, LINE, 1, "4 4")
    d.text(x0 + 8, fy + 16, "calm", 9.5, 600, MUTED)
    d.text(x0 + 8, fy + fh - 8, "anxious", 9.5, 600, MUTED)
    for vals, color, dash in (([-0.6, -0.2, -0.3, -0.9, -0.5, -0.7], TILE["red"], "5 4"),
                              ([-0.4, 0.2, 0.3, 0.7, 0.8, 0.9], TILE["green"], None)):
        pts = [(x0 + i * cw + (cw - 6) / 2, base - v * amp) for i, v in enumerate(vals)]
        path = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            mx = (xa + xb) / 2
            path += f" C{mx:.1f},{ya:.1f} {mx:.1f},{yb:.1f} {xb:.1f},{yb:.1f}"
        da = f' stroke-dasharray="{dash}"' if dash else ""
        d.raw(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.2"{da}/>')
        for xp, yp in pts:
            d.circle(xp, yp, 4, PAPER, color, 1.8)
    for label, (y, h, _) in list(rows.items()) + [("Feeling", (fy, fh, None))]:
        yy = y + h / 2
        d.raw(f'<text x="{LW - 6}" y="{yy}" font-size="10" font-weight="700" fill="{MUTED}" '
              f'transform="rotate(90 {LW - 6} {yy})" text-anchor="middle">{label}</text>')
    d.legend(x0 + 8, 400, [("dash", TILE["red"], "today (PDF + web search)"), ("line", TILE["green"], "with Nabz")])
    return d


FIGURES = {
    "architecture": architecture, "deployment": deployment, "pipeline": pipeline, "use-case": use_case,
    "activity-a": activity_a, "activity-b": activity_b, "sequence-a": sequence_a, "sequence-b": sequence_b,
    "state-machine": state_machine, "er-a": er_a, "er-b": er_b, "class-a": class_a, "class-b": class_b,
    "gantt": gantt, "lifecycle": lifecycle, "user-journey": journey,
}


def main(names: list[str]) -> None:
    OUT.mkdir(exist_ok=True)
    for name in names or FIGURES:
        FIGURES[name]().save(OUT / f"{name}.svg")
        print(f"wrote docs/diagrams/report/{name}.svg")


if __name__ == "__main__":
    main(sys.argv[1:])
