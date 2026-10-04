"""Report edition of the Nabz figures — drawn at printed size for the A4 college report, and drawn from the
system as built (October 2026), not the plan.

    python docs/diagrams/src/report.py            # all figures → docs/diagrams/report/
    python docs/diagrams/src/report.py er-a gantt # a subset

Page geometry (A4, 1-inch margins): the text block is 15.9 cm × 24.6 cm, i.e.
602 × 930 px at 96 px/in. Portrait figures are 602 px wide; landscape figures
(placed on a landscape page) are 930 px wide and at most ~560 px tall.
Figures are written with physical sizes (cm), so inserting them into Word at
100 % gives the intended print size. At that size the smallest text is
9.5 px ≈ 7 pt and body labels are 10.5–12.5 px ≈ 8–9.5 pt.

Connectors run in the gaps between boxes and never across a label. No titles
are drawn inside the figures: the report adds a numbered caption below each
figure, as the college template requires.
"""

from __future__ import annotations

import csv
import sys
from datetime import date, timedelta

from build import KIND, OWNER, SRC, _wrap, actor
from nordsvg import (
    EDGE, INK, INK_2, LINE, MONO, MUTED, PAPER, RED, SNOW, SNOW_2, TILE,
    Diagram, icon, text_width,
)

OUT = SRC.parent / "report"
PW, LW = 602, 930          # portrait / landscape text-block width in px
ORANGE = TILE["orange"]


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
    d = page(PW, 676)
    chip(d, 72, 6, "users", "slate", "Users", "families · doctors · clinical reviewers · admins")
    # the Users arrow comes down at x = 89, so these two titles sit to its right
    d.group(10, 70, 582, 480, "", "slate", "laptop", tint=False)
    d.text(106, 88.5, "Docker host", 12.5, 600, INK)
    d.text(106 + text_width("Docker host", 12.5, 600) + 10, 88.5, "one Compose project", 11, 400, MUTED)
    d.group(24, 108, 180, 428, "", "cyan", "browser")
    d.text(106, 126.5, "Presentation", 12.5, 600, INK)
    d.group(212, 108, 176, 428, "Application", "blue", "api")
    d.group(396, 108, 182, 428, "Data & processing", "green", "database")
    s = 40
    d.node(89, 180, "Web app", "browser", "cyan", ["React · TypeScript", "English · Hindi · Odia"], s)
    d.node(89, 330, "3D body map", "body", "cyan", ["three.js, drawn in code", "flat view as fallback"], s)
    d.node(300, 180, "API", "api", "blue", ["FastAPI · REST · SSE", "auth · consent · sharing"], s)
    d.node(300, 330, "Uploads volume", "disk", "blue", ["reports · records", "narration audio"], s)
    d.node(300, 462, "Mailpit", "mail", "blue", ["email in development"], s)
    d.node(487, 180, "PostgreSQL 17", "database", "green", ["+ pgvector", "records · jobs · vectors"], s)
    d.node(487, 330, "Worker", "gear", "green", ["extract · analyse", "explain · reminders"], s)
    d.node(487, 462, "Data files", "folder", "green", ["catalogue · e5 model", "confidence model"], s)
    c = INK_2
    d.arrow([(89, 40), (89, 158)], c)
    d.arrow([(110, 180), (279, 180)], c, tail="arrow", label="REST · SSE", label_at=(197, 180))
    d.arrow([(321, 180), (466, 180)], c, label="SQL", label_at=(392, 180))
    d.arrow([(487, 256), (487, 309)], c, tail="arrow", label="jobs · results", label_at=(487, 282))
    d.arrow([(300, 256), (300, 309)], c, label="store files", label_at=(300, 282))
    d.arrow([(466, 330), (321, 330)], c, label="read files", label_at=(392, 330))
    d.arrow([(487, 404), (487, 441)], c, label="load", label_at=(487, 422))
    d.arrow([(89, 256), (89, 309)], c, dash="5 4")
    d.arrow([(279, 190), (219, 190), (219, 462), (279, 462)], c, dash="5 4")
    d.text(225, 448, "SMTP", 9.5, 600, MUTED)
    d.arrow([(300, 551), (300, 583)], ORANGE, label="API and worker · HTTPS 443", label_at=(300, 567),
            label_color=ORANGE)
    d.group(10, 584, 582, 84, "External services", "orange", "cloud", dashed=True,
            sublabel="only with consent · de-identified values, never a name")
    chip(d, 40, 624, "sparkle", "orange", "Groq · gpt-oss-120b", "explanations · answers · safety judge")
    chip(d, 330, 624, "speaker", "orange", "ElevenLabs", "narration, made on first play")
    return d


# =============================================================================
# Deployment — portrait
# =============================================================================
def deployment() -> Diagram:
    d = page(PW, 580)
    d.group(6, 6, 590, 452, "Developer laptop", "slate", "laptop", tint=False, sublabel="Windows 11 · 16 GB RAM · no GPU")
    d.group(20, 46, 562, 400, "Docker Desktop", "slate", "cube", dashed=True, tint=False, sublabel="WSL 2")
    d.group(34, 86, 534, 260, "Compose project nabz", "blue", "network", dashed=True)

    def box(x, y, name, glyph, role, rows):
        d.rect(x, y, 160, 88, fill=PAPER, stroke=EDGE[role], sw=1.3, rx=6)
        d.rect(x + 10, y + 10, 24, 24, fill=TILE[role], stroke="none", rx=5)
        d.raw(icon(glyph, x + 14, y + 14, 16))
        d.text(x + 42, y + 27, name, 12, 700, INK, family=MONO)
        for i, r in enumerate(rows):
            d.text(x + 12, y + 52 + i * 15, r, 10, 400, INK_2)

    box(48, 126, "web", "browser", "cyan", ["node:22-alpine · Vite", "127.0.0.1:5173"])
    box(222, 126, "api", "api", "blue", ["python:3.12 + uv · FastAPI", "127.0.0.1:8000"])
    box(396, 126, "worker", "gear", "blue", ["same image as api", "no published port"])
    box(222, 242, "db", "database", "green", ["pgvector/pgvector:pg17", "127.0.0.1:5433 → 5432"])
    box(396, 242, "mailpit", "mail", "slate", ["axllent/mailpit", "inbox on 127.0.0.1:8025"])
    d.rect(48, 242, 160, 88, fill=SNOW, stroke="none", rx=6)
    d.text(60, 262, "Volumes and mounts", 11, 700, INK)
    d.lines(60, 280, ["pgdata ← db", "uploads ← api, worker", "./data → /srv/data", "(catalogue, models)"],
            10, 400, INK_2, leading=1.32)
    d.arrow([(208, 170), (221, 170)], INK_2)
    d.arrow([(302, 215), (302, 241)], INK_2)
    d.arrow([(430, 215), (430, 228), (342, 228), (342, 241)], INK_2)
    d.arrow([(520, 215), (520, 241)], INK_2)
    d.text(48, 370, "Published ports — bound to 127.0.0.1, not reachable from the LAN", 10.5, 650, INK_2)
    for i, (p, s_) in enumerate([(":5173", "web"), (":8000", "api"), (":5433", "db"), (":8025", "mailpit")]):
        x = 48 + i * 130
        d.rect(x, 382, 120, 26, fill=SNOW, stroke=LINE, rx=13)
        d.text(x + 12, 399, p, 10.5, 700, INK, family=MONO)
        d.text(x + 60, 399, s_, 10.5, 400, INK_2)
    d.text(48, 432, "compose.offline.yaml moves db, api and worker to a network with no route out (offline demo).",
           9.5, 400, MUTED, italic=True)
    d.arrow([(557, 170), (574, 170), (574, 486)], ORANGE)
    d.group(6, 474, 590, 98, "Egress · HTTPS 443", "orange", "globe", dashed=True, sublabel="only with consent")
    chip(d, 30, 516, "sparkle", "orange", "Groq API", "explanations · answers")
    chip(d, 222, 516, "speaker", "orange", "ElevenLabs API", "narration")
    chip(d, 410, 516, "book", "orange", "MedlinePlus", "knowledge build, once")
    return d


# =============================================================================
# Pipeline — portrait (three columns)
# =============================================================================
def pipeline() -> Diagram:
    cols = [
        ("A · Ingest & extract", "automatic", [
            ("Upload & validate", "rule", "type · size · consent", "FastAPI"),
            ("Clean the image", "rule", "deskew · contrast (photos)", "OpenCV"),
            ("Read the text", "ml", "text layer, else OCR", "pypdfium2 · RapidOCR"),
            ("Parse rows", "rule", "name · value · unit · range", "layout rules"),
            ("Map to catalogue", "ml", "aliases + fuzzy match", "RapidFuzz · 70 tests"),
            ("Convert & score", "ml", "units · row confidence", "logistic model"),
        ]),
        ("B · Verify & analyse", "the person confirms first", [
            ("Human review", "human", "weak rows first, by the page", "web app"),
            ("Classify", "rule", "lab's range, else typical", "Python rules"),
            ("Critical limits", "rule", "fixed 'see a doctor today'", "reviewed table"),
            ("Change & trend", "ml", "RCV · Theil–Sen · M–K", "NumPy"),
            ("Percentile", "ml", "same age band and sex", "NHANES 2017–20"),
        ]),
        ("C · Explain & present", "grounded · checked", [
            ("Retrieve", "ml", "cited MedlinePlus passages", "pgvector · e5-small"),
            ("Explain", "genai", "summary · results · questions", "gpt-oss-120b · Groq"),
            ("Safety checks", "rule", "rules + judge, else template", "validator"),
            ("Narrate", "genai", "on first play · EN HI OR", "ElevenLabs"),
            ("Present", "rule", "body map · story · Ask Nabz", "React · three.js"),
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
    d.pill(301, y + 8, "nothing is analysed before the values are confirmed · the model never sees a name",
           TILE["slate"], 10)
    d.legend(10, y + 38, [("box", TILE[r], lbl) for r, lbl in KIND.values()])
    return d


# =============================================================================
# Use-case model — portrait
# =============================================================================
def use_case() -> Diagram:
    d = page(PW, 836)
    d.rect(96, 4, 432, 752, fill=SNOW, stroke=INK_2, sw=1.2, rx=8, opacity=0.5)
    d.text(110, 22, "Nabz", 12.5, 700, INK)
    a, b, rx, ry = 208, 420, 94, 22

    def uc(cx, cy, code, name, role="blue"):
        d.raw(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{PAPER}" stroke="{EDGE[role]}" stroke-width="1.4"/>')
        d.text(cx, cy - 3, code, 9.5, 600, TILE[role], "middle")
        d.text(cx, cy + 11, name, 10.5, 600, INK, "middle")

    col_a = [("UC-01", "Sign up / sign in"), ("UC-02", "Manage family profiles"), ("UC-04", "Upload a lab report"),
             ("UC-05", "Review & correct values"), ("UC-06", "Explore the 3D body map"),
             ("UC-07", "Trends, story & readings"), ("UC-11", "Share with a doctor"),
             ("UC-12", "Export / delete data"), ("UC-08", "Read & ask about results")]
    ys = [52 + i * 56 for i in range(9)]
    for (code, name), y in zip(col_a, ys):
        uc(a, y, code, name)
    actor(d, 44, 270, "Family")
    d.text(44, 330, "member", 12.5, 650, INK, "middle")
    for y in ys:
        d.line(62, 254, a - rx, y, INK_2, 1.1)
    col_b = [("UC-14", "Curate the catalogue", 52, "orange"), ("UC-15", "Manage knowledge base", 108, "orange"),
             ("UC-03", "Give / withdraw consent", 164, "green"), ("UC-16", "Safety review & audit", 220, "orange"),
             ("UC-10", "Questions for the doctor", 444, "blue"), ("UC-18", "Grounded explanation", 500, "purple"),
             ("UC-13", "Critical-value alert", 556, "red"), ("UC-09", "Listen to explanation", 612, "purple"),
             ("UC-17", "Open a shared link", 672, "cyan"), ("UC-19", "Read shared reports, note", 728, "cyan")]
    for code, name, y, role in col_b:
        uc(b, y, code, name, role)

    def dep(p1, p2, kind, t=0.5):
        d.arrow([p1, p2], INK_2, sw=1.1, dash="4 3", head="open")
        d.pill(p1[0] + (p2[0] - p1[0]) * t, p1[1] + (p2[1] - p1[1]) * t, kind, MUTED, 9.5)

    dep((a + rx, 164), (b - rx, 164), "«include»")
    dep((a + 80, 489), (b - 80, 455), "«include»")
    dep((a + rx, 500), (b - rx, 500), "«include»")
    dep((b - 94, 556), (a + 72, 516), "«extend»")
    dep((b - 88, 606), (a + 46, 521), "«extend»", 0.45)
    actor(d, 44, 700, "Doctor")
    d.line(62, 684, b - rx, 672, INK_2, 1.1)
    d.line(62, 690, b - rx, 728, INK_2, 1.1)
    d.text(236, 666, "link · no account", 9, 400, MUTED, "middle", italic=True)
    d.text(236, 734, "verified clinician account", 9, 400, MUTED, "middle", italic=True)
    actor(d, 568, 92, "Admin")
    for y in (52, 108, 220):
        d.line(552, 84, b + rx, y, INK_2, 1.1)
    actor(d, 568, 262, "Reviewer")
    d.line(552, 252, b + rx, 220, INK_2, 1.1)
    for y, lbl in ((500, "Groq"), (612, "ElevenLabs")):
        d.rect(531, y - 20, 68, 40, fill=PAPER, stroke=EDGE["purple"], sw=1.3, rx=5)
        d.text(565, y - 5, "«system»", 9, 500, MUTED, "middle")
        d.text(565, y + 10, lbl, 10, 700, INK, "middle")
        d.line(531, y, b + rx, y, INK_2, 1.1)
    d.rect(110, 768, 404, 30, fill=PAPER, stroke=EDGE["red"], sw=1.1, rx=6)
    d.text(122, 787, "Out of scope: diagnosis · prescribing or dosing · emergency triage", 10.5, 600, TILE["red"])
    d.legend(96, 820, [("line", INK_2, "association"), ("dash", INK_2, "«include» / «extend»")])
    return d


# =============================================================================
# Activity diagram — portrait, two parts
# =============================================================================
LANES = [("User", "slate"), ("Web app", "cyan"), ("API", "blue"), ("Worker", "blue"), ("AI models", "purple")]


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
        ("a1", "act", "User", 98, ["Photograph or", "choose the report"], "slate"),
        ("a2", "act", "Web", 168, ["Check type", "and size"], "cyan"),
        ("a3", "act", "API", 240, ["Check consent,", "store the file,", "queue extraction"]),
        ("a4", "act", "Worker", 318, ["Claim the job"]),
        ("d1", "dec", "Worker", 384, ["text layer?"]),
        ("a5", "act", "AI", 384, ["Clean the image,", "OCR (RapidOCR)"], "purple"),
        ("m1", "dec", "Worker", 456, []),
        ("a6", "act", "Worker", 524, ["Parse rows, map,", "convert, score"]),
        ("a7", "act", "Web", 598, ["Values beside the", "page, weakest first"], "cyan"),
        ("a8", "act", "User", 668, ["Correct or", "confirm values"], "slate"),
        ("c", "conn", "User", 738, ["A"]),
    ]
    flows = [("s", "a1", None), ("a1", "a2", None), ("a2", "a3", None), ("a3", "a4", None), ("a4", "d1", None),
             ("d1", "m1", "[yes]"), ("m1", "a6", None), ("a6", "a7", None), ("a7", "a8", None), ("a8", "c", None)]

    def extra(d, cx, N):
        x, y = N["d1"][:2]
        d.arrow([(x + 15, y), (cx["AI"] - 54, y)], INK_2, sw=1.2)
        d.text(x + 22, y + 14, "[no]", 9.5, 600, MUTED)
        ax, ay, _, ah = N["a5"]
        d.arrow([(ax, ay + ah), (ax, 456), (x + 15, 456)], INK_2, sw=1.2)
        d.text(cx["User"] + 16, 742, "continues in part (b)", 9.5, 500, MUTED)

    return _activity(770, spec, flows, extra)


def activity_b() -> Diagram:
    spec = [
        ("c", "conn", "User", 40, ["A"]),
        ("b1", "act", "API", 96, ["Mark verified,", "queue analysis"]),
        ("b2", "act", "Worker", 166, ["Status · critical", "change · trend", "percentile"]),
        ("d3", "dec", "Worker", 232, ["critical?"]),
        ("d4", "dec", "Worker", 296, []),
        ("b3", "act", "AI", 296, ["Retrieve passages,", "write explanation"], "purple"),
        ("b4", "act", "Worker", 372, ["Rule checks", "+ model judge"], "red"),
        ("d5", "dec", "Worker", 440, []),
        ("b5", "act", "Worker", 510, ["Template built", "from the values"], "slate"),
        ("m", "dec", "Worker", 576, []),
        ("b6", "act", "Web", 640, ["Body map, cards", "and explanation"], "cyan"),
        ("b7", "act", "User", 706, ["Explore · ask", "share · listen"], "slate"),
        ("b8", "act", "AI", 706, ["Narrate on first", "play (ElevenLabs)"], "purple", True),
        ("e", "end", "User", 768, []),
    ]
    flows = [("c", "b1", None), ("b1", "b2", None), ("b2", "d3", None), ("d3", "d4", "[no]"), ("b3", "b4", None),
             ("b4", "d5", None), ("d5", "b5", "[no]"), ("b5", "m", None), ("m", "b6", None), ("b6", "b7", None),
             ("b7", "e", None)]

    def extra(d, cx, N):
        xw, xa = cx["Worker"], cx["API"]
        # critical, or no consent: the template, never generated prose
        d.arrow([(xw - 15, 232), (xa, 232), (xa, 510), (xw - 54, 510)], INK_2, sw=1.2)
        d.text(xw - 20, 226, "[yes]", 9.5, 600, MUTED, "end")
        d.text(xw - 20, 281, "AI consent?", 10, 500, INK_2, "end")
        d.arrow([(xw - 15, 296), (xa, 296)], INK_2, sw=1.2, head=None)
        d.circle(xa, 296, 2.6, INK_2)
        d.text(xw - 20, 310, "[no]", 9.5, 600, MUTED, "end")
        d.arrow([(xw + 15, 296), (cx["AI"] - 54, 296)], INK_2, sw=1.2)
        d.text(xw + 20, 310, "[yes]", 9.5, 600, MUTED)
        d.text(xw - 20, 425, "passed?", 10, 500, INK_2, "end")
        d.arrow([(xw + 15, 440), (xw + 66, 440), (xw + 66, 576), (xw + 15, 576)], INK_2, sw=1.2)
        d.text(xw + 20, 434, "[yes]", 9.5, 600, MUTED)
        d.arrow([(cx["User"] + 54, 716), (cx["AI"] - 54, 716)], INK_2, sw=1.2, dash="5 4")
        d.text(cx["API"], 730, "voice consent", 9.5, 500, MUTED, "middle")

    return _activity(790, spec, flows, extra)


# =============================================================================
# Sequence diagram — portrait, two parts
# =============================================================================
EXTERNAL = {"Groq", "ElevenLabs"}


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
        color = ORANGE if EXTERNAL & {src, dst} else INK_2
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
             ("RapidOCR", "purple")]
    msgs = [
        ("User", "Web app", "choose photo / PDF"),
        ("Web app", "API", "POST …/reports"),
        ("API", "API", "type · size · consent"),
        ("API", "PostgreSQL", "INSERT report + job"),
        ("API", "Web app", "202 Accepted", "r"),
        ("Web app", "API", "GET …/events (SSE)"),
        ("Worker", "PostgreSQL", "claim job (SKIP LOCKED)"),
        ("frame+", "opt", "[photo or scan]", "Worker", "RapidOCR"),
        ("Worker", "RapidOCR", "cleaned page"),
        ("RapidOCR", "Worker", "words + boxes", "r"),
        ("frame-",),
        ("Worker", "Worker", "parse · map · score"),
        ("Worker", "PostgreSQL", "INSERT observations"),
        ("API", "Web app", "status: needs_review", "r"),
        ("Web app", "User", "review screen", "r"),
    ]
    return _sequence(parts, msgs, 50, 100)


def sequence_b() -> Diagram:
    parts = [("User", "slate"), ("Web app", "cyan"), ("API", "blue"), ("PostgreSQL", "green"), ("Worker", "blue"),
             ("Groq", "orange"), ("ElevenLabs", "orange")]
    msgs = [
        ("User", "Web app", "confirm values"),
        ("Web app", "API", "POST …/confirm"),
        ("API", "PostgreSQL", "verified · enqueue"),
        ("Worker", "PostgreSQL", "claim · load history"),
        ("Worker", "Worker", "status · critical · trend"),
        ("Worker", "PostgreSQL", "kNN passages (pgvector)"),
        ("frame+", "opt", "[consent, not critical]", "Worker", "Groq"),
        ("Worker", "Groq", "values, no names"),
        ("Groq", "Worker", "explanation JSON", "r"),
        ("Worker", "Worker", "rule checks"),
        ("Worker", "Groq", "safety judge"),
        ("Groq", "Worker", "safe / problems", "r"),
        ("frame-",),
        ("Worker", "PostgreSQL", "save (else template)"),
        ("Web app", "API", "GET …/insights"),
        ("API", "Web app", "organs · values · text", "r"),
        ("frame+", "opt", "[play · voice consent]", "Web app", "ElevenLabs"),
        ("Web app", "API", "POST …/audio"),
        ("API", "ElevenLabs", "text + language"),
        ("ElevenLabs", "API", "MP3", "r"),
        ("API", "Web app", "audio stream", "r"),
        ("frame-",),
    ]
    return _sequence(parts, msgs, 44, 85.5)


# =============================================================================
# State machine — portrait (vertical)
# =============================================================================
def state_machine() -> Diagram:
    d = page(PW, 744)

    def st(x, y, name, code, role="blue", w=150):
        d.rect(x - w / 2, y - 21, w, 42, fill=PAPER, stroke=EDGE[role], sw=1.5, rx=13)
        d.text(x, y - 2, name, 11.5, 650, INK, "middle")
        d.text(x, y + 13, code, 9.5, 400, MUTED, "middle", family=MONO)

    def lab(x, y, s, color=INK_2, anchor="start"):
        d.text(x, y, s, 10, 500, color, anchor)

    X = 300
    d.circle(X, 12, 8, INK)
    st(X, 64, "Queued", "queued", "slate")
    d.rect(150, 112, 300, 94, fill=SNOW, stroke=TILE["blue"], sw=1.4, rx=14)
    d.text(164, 130, "Processing", 11.5, 700, INK)
    d.text(236, 130, "processing", 9.5, 400, MUTED, family=MONO)
    for i, s in enumerate(["Pre-process", "Read text", "Parse & map"]):
        bx = 176 + i * 96
        d.rect(bx, 150, 82, 34, fill=PAPER, stroke=EDGE["blue"], sw=1.3, rx=10)
        d.text(bx + 41, 171, s, 10.5, 600, INK, "middle")
        if i < 2:
            d.arrow([(bx + 83, 167), (bx + 95, 167)], INK_2, sw=1.1)
    st(X, 258, "Needs review", "needs_review", "orange")
    st(X, 338, "Verified", "verified", "green")
    st(X, 418, "Analysing", "analysing")
    st(X, 498, "Explaining", "explaining", "purple")
    st(X, 578, "Explained", "explained", "green")
    st(510, 458, "Failed", "failed", "red", 130)
    st(96, 680, "Deleted", "removed at once", "slate", 130)
    d.circle(400, 680, 10, PAPER, INK, 1.5)
    d.circle(400, 680, 6, INK)

    a = dict(color=INK_2, sw=1.3)
    d.arrow([(X, 20), (X, 42)], **a); lab(X + 10, 34, "upload accepted (type · size · consent)")
    d.arrow([(X, 85), (X, 111)], **a); lab(X + 8, 102, "claimed")
    d.arrow([(X, 207), (X, 236)], **a); lab(X + 8, 225, "draft saved")
    d.arrow([(X, 279), (X, 316)], **a); lab(X + 8, 302, "user confirms")
    d.arrow([(X, 359), (X, 396)], **a); lab(X + 8, 382, "claimed")
    d.arrow([(X, 439), (X, 476)], **a); lab(X + 8, 462, "analysed")
    d.arrow([(X, 519), (X, 556)], **a); lab(X + 8, 536, "saved (model"); lab(X + 8, 549, "or template)")
    lab(24, 64, "A refused upload creates", MUTED)
    lab(24, 78, "no report at all.", MUTED)
    # retry while attempts are left (the same holds for analysis and explanation)
    d.arrow([(451, 140), (474, 140), (474, 64), (376, 64)], color=INK_2, sw=1.2, dash="5 4")
    lab(482, 92, "error, tries left")
    lab(482, 106, "→ wait again")
    # attempts used up
    d.arrow([(451, 186), (590, 186), (590, 458), (576, 458)], color=RED, sw=1.3)
    lab(500, 180, "3rd failure", RED)
    d.arrow([(376, 418), (480, 418), (480, 436)], color=RED, sw=1.3)
    d.arrow([(376, 490), (480, 490), (480, 480)], color=RED, sw=1.3)
    lab(445, 512, "admin can retry", MUTED)
    lab(445, 525, "from the console", MUTED)
    # re-explained
    d.arrow([(376, 578), (410, 578), (410, 506), (376, 506)], color=INK_2, sw=1.2, dash="5 4")
    lab(418, 560, "another language, or")
    lab(418, 574, "details or limits changed")
    # deletion
    d.arrow([(224, 578), (96, 578), (96, 658)], **a); lab(104, 600, "user deletes")
    d.arrow([(162, 680), (389, 680)], **a); lab(172, 672, "rows and files removed")
    d.text(300, 726, "A report can be deleted in any state; only an audit entry without health data remains.", 10,
           500, MUTED, "middle", italic=True)
    return d


# =============================================================================
# ER diagram — portrait, two parts (key columns only)
# =============================================================================
TABLES: dict[str, tuple[str, list[tuple[str, str, str]]]] = {
    # identity & governance
    "app_user": ("slate", [("PK", "id", "uuid"), ("UQ", "email", "citext"), ("", "role", "user_role"),
                           ("", "totp_enabled_at", "timestamptz")]),
    "user_session": ("slate", [("PK", "id", "uuid"), ("FK", "user_id", "uuid"), ("UQ", "token_hash", "text"),
                               ("", "revoked_at", "timestamptz")]),
    "auth_token": ("slate", [("PK", "id", "uuid"), ("FK", "user_id", "uuid"), ("", "purpose", "token_purpose"),
                             ("", "expires_at", "timestamptz")]),
    "audit_log": ("orange", [("PK", "id", "bigint"), ("FK", "actor_user_id", "uuid"), ("", "action", "text"),
                             ("", "entity_type", "text")]),
    "clinician": ("orange", [("PK", "user_id", "uuid"), ("", "registration_no", "text"), ("", "council", "text"),
                             ("", "verified_at", "timestamptz")]),
    "clinician_note": ("orange", [("PK", "id", "uuid"), ("FK", "report_id", "uuid"),
                                  ("FK", "clinician_user_id", "uuid"), ("", "text", "text")]),
    # people & care
    "profile": ("slate", [("PK", "id", "uuid"), ("FK", "owner_user_id", "uuid"), ("", "display_name", "text"),
                          ("", "date_of_birth", "date"), ("", "guardian_confirmed_at", "timestamptz")]),
    "consent": ("slate", [("PK", "id", "uuid"), ("FK", "user_id", "uuid"), ("FK", "profile_id", "uuid"),
                          ("", "purpose", "consent_purpose"), ("", "revoked_at", "timestamptz")]),
    "health_record": ("blue", [("PK", "id", "uuid"), ("FK", "profile_id", "uuid"), ("", "kind", "record_kind"),
                               ("", "storage_key", "text")]),
    "reminder": ("blue", [("PK", "id", "uuid"), ("FK", "profile_id", "uuid"), ("", "due_on", "date"),
                          ("", "repeat_months", "smallint")]),
    "home_reading": ("blue", [("PK", "id", "uuid"), ("FK", "profile_id", "uuid"), ("", "kind", "reading_kind"),
                              ("", "value", "numeric"), ("", "value2", "numeric")]),
    "share_link": ("orange", [("PK", "id", "uuid"), ("FK", "report_id", "uuid"), ("UQ", "token_hash", "text"),
                              ("", "expires_at", "timestamptz")]),
    # reports
    "report": ("blue", [("PK", "id", "uuid"), ("FK", "profile_id", "uuid"), ("FK", "uploaded_by", "uuid"),
                        ("", "status", "report_status"), ("", "collected_at", "date")]),
    "report_file": ("blue", [("PK", "id", "uuid"), ("FK", "report_id", "uuid"), ("", "storage_key", "text"),
                             ("", "mime_type", "text")]),
    "report_page": ("blue", [("PK", "id", "uuid"), ("FK", "report_file_id", "uuid"), ("", "page_no", "smallint"),
                             ("", "ocr", "jsonb")]),
    "observation": ("blue", [("PK", "id", "uuid"), ("FK", "report_id", "uuid"), ("FK", "report_page_id", "uuid"),
                             ("FK", "test_id", "int"), ("", "value_num", "numeric"), ("", "status", "obs_status"),
                             ("", "confidence", "real")]),
    "processing_job": ("blue", [("PK", "id", "bigint"), ("FK", "report_id", "uuid"), ("", "stage", "job_stage"),
                                ("", "status", "job_status"), ("", "attempts", "smallint")]),
    "report_grant": ("orange", [("PK", "id", "uuid"), ("FK", "report_id", "uuid"),
                                ("FK", "clinician_user_id", "uuid"), ("", "revoked_at", "timestamptz")]),
    # catalogue
    "organ_system": ("green", [("PK", "id", "smallint"), ("UQ", "code", "text"), ("", "name_en", "text"),
                               ("", "name_or", "text")]),
    "lab_test": ("green", [("PK", "id", "int"), ("UQ", "code", "text"), ("UQ", "loinc_code", "text"),
                           ("FK", "organ_system_id", "smallint"), ("", "canonical_unit", "text"),
                           ("", "aliases", "text[]")]),
    "unit_conversion": ("green", [("PK", "id", "int"), ("FK", "test_id", "int"), ("", "from_unit", "text"),
                                  ("", "factor", "numeric")]),
    "reference_range": ("green", [("PK", "id", "int"), ("FK", "test_id", "int"), ("", "sex", "sex"),
                                  ("", "low", "numeric"), ("", "high", "numeric")]),
    "critical_limit": ("green", [("PK", "id", "int"), ("FK", "test_id", "int"), ("", "low", "numeric"),
                                 ("", "high", "numeric"), ("", "reviewed_by", "text"),
                                 ("", "proposed_at", "timestamptz")]),
    "population_percentile": ("green", [("PK", "id", "int"), ("FK", "test_id", "int"), ("", "sex", "sex"),
                                        ("", "age_band", "int4range"), ("", "p50", "numeric")]),
    "catalogue_revision": ("green", [("PK", "id", "smallint"), ("", "revision", "int"),
                                     ("", "changed_at", "timestamptz")]),
    # knowledge & AI
    "kb_document": ("purple", [("PK", "id", "uuid"), ("", "title", "text"), ("", "url", "text"),
                               ("", "license", "text")]),
    "kb_chunk": ("purple", [("PK", "id", "uuid"), ("FK", "document_id", "uuid"), ("FK", "test_id", "int"),
                            ("", "embedding", "vector(384)")]),
    "trend_insight": ("purple", [("PK", "id", "uuid"), ("FK", "profile_id", "uuid"), ("FK", "test_id", "int"),
                                 ("", "direction", "text"), ("", "confirmed", "boolean")]),
    "explanation": ("purple", [("PK", "id", "uuid"), ("FK", "report_id", "uuid"), ("", "language", "lang"),
                               ("", "prompt_version", "text"), ("", "safety_status", "safety_status")]),
    "explanation_citation": ("purple", [("PK", "explanation_id", "uuid"), ("PK", "kb_chunk_id", "uuid"),
                                        ("", "rank", "smallint")]),
    "feedback": ("purple", [("PK", "id", "uuid"), ("FK", "explanation_id", "uuid"), ("FK", "user_id", "uuid"),
                            ("", "rating", "smallint")]),
    "report_question": ("purple", [("PK", "id", "uuid"), ("FK", "report_id", "uuid"), ("", "question", "text"),
                                   ("", "mode", "text"), ("", "refusal", "text")]),
    "safety_review": ("orange", [("PK", "id", "uuid"), ("FK", "reviewer_id", "uuid"), ("", "subject_type", "text"),
                                 ("", "verdict", "text")]),
}
ER_W, ER_HEAD, ER_ROW = 160, 20, 13


def _er(height: int, place: dict, rels: list, notes: list[str]) -> Diagram:
    d = page(PW, height)
    box = {}
    for name, (x, y) in place.items():
        role, cols = TABLES[name]
        h = ER_HEAD + len(cols) * ER_ROW + 5
        box[name] = (x, y, h)
        d.rect(x, y, ER_W, h, fill=PAPER, stroke=EDGE[role], sw=1.3, rx=4)
        d.rect(x, y, ER_W, ER_HEAD, fill=TILE[role], stroke="none", rx=4)
        d.rect(x, y + ER_HEAD - 4, ER_W, 4, fill=TILE[role], stroke="none", rx=0)
        d.text(x + 8, y + 14.5, name, 10.5, 700, PAPER, family=MONO)
        for i, (k, col, typ) in enumerate(cols):
            ry = y + ER_HEAD + 2 + i * ER_ROW
            kc = {"PK": TILE["orange"], "FK": TILE["blue"], "UQ": TILE["green"]}.get(k, MUTED)
            d.text(x + 6, ry + 10, k, 8, 700, kc, family=MONO)
            d.text(x + 26, ry + 10, col, 9.5, 600 if k == "PK" else 400, INK, family=MONO)
            if 26 + len(col) * 5.7 + 6 < ER_W - 6 - len(typ) * 5.1:  # the type only where it fits
                d.text(x + ER_W - 6, ry + 10, typ, 8.5, 400, MUTED, "end", family=MONO)

    def ry(ent, col):
        x, y, _ = box[ent]
        i = [c for _, c, _ in TABLES[ent][1]].index(col)
        return y + ER_HEAD + 2 + i * ER_ROW + ER_ROW / 2

    def pt(ent, side, col=None):
        x, y, h = box[ent]
        return {"L": (x, ry(ent, col) if col else y + h / 2), "R": (x + ER_W, ry(ent, col) if col else y + h / 2),
                "T": (x + ER_W / 2, y), "B": (x + ER_W / 2, y + h)}[side]

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
            tick(9)
        if kind == "one":
            tick(13)
        if kind in ("one_many", "zero_many"):
            parts.append(f"M{x1 + px * 5.5:.1f},{y1 + py * 5.5:.1f} L{x1 + ux * 8:.1f},{y1 + uy * 8:.1f} "
                         f"L{x1 - px * 5.5:.1f},{y1 - py * 5.5:.1f}")
        if kind == "zero_one":
            tick(8)
        d.raw(f'<path d="{" ".join(parts)}" stroke="{INK_2}" stroke-width="1.2" fill="none"/>')
        if kind in ("zero_many", "zero_one"):
            t = 15 if kind == "zero_many" else 14
            d.circle(x1 + ux * t, y1 + uy * t, 3.3, PAPER, INK_2, 1.2)

    for (e1, s1, c1), (e2, s2, c2), k1, k2, via in rels:
        p1, p2 = pt(e1, s1, c1), pt(e2, s2, c2)
        pts = [p1, p2] if via is None or abs(p1[1] - p2[1]) < 0.5 else [p1, (via, p1[1]), (via, p2[1]), p2]
        d.arrow(pts, INK_2, sw=1.15, head=None)
        end(pts[0], pts[1], k1)
        end(pts[-1], pts[-2], k2)
    y = height - 10 - 13 * (len(notes) - 1)
    for i, s in enumerate(notes):
        d.text(20, y + i * 13, s, 9.5, 400, MUTED)
    return d


C0, C1, C2 = 26, 231, 436       # 45 px gaps: room for a bus and its end markers
LEFT, GAP1, GAP2 = 6, 208, 413   # bus positions


def er_a() -> Diagram:
    """Accounts, people, care, reports and sharing (18 tables)."""
    place = {"app_user": (C0, 6), "user_session": (C0, 112), "auth_token": (C0, 210), "audit_log": (C0, 308),
             "clinician": (C0, 406), "clinician_note": (C0, 504),
             "profile": (C1, 6), "consent": (C1, 120), "health_record": (C1, 236), "reminder": (C1, 334),
             "home_reading": (C1, 432), "share_link": (C1, 546),
             "report": (C2, 6), "report_file": (C2, 120), "report_page": (C2, 218), "observation": (C2, 316),
             "processing_job": (C2, 456), "report_grant": (C2, 570)}
    rels = [
        (("app_user", "B", None), ("user_session", "T", None), "one", "zero_many", None),
        (("app_user", "L", "id"), ("auth_token", "L", "user_id"), "one", "zero_many", LEFT),
        (("app_user", "L", "id"), ("audit_log", "L", "actor_user_id"), "zero_one", "zero_many", LEFT),
        (("app_user", "L", "id"), ("clinician", "L", "user_id"), "one", "zero_one", LEFT),
        (("app_user", "L", "id"), ("clinician_note", "L", "clinician_user_id"), "zero_one", "zero_many", LEFT),
        (("app_user", "R", "email"), ("profile", "L", "owner_user_id"), "one", "zero_many", GAP1),
        (("profile", "B", None), ("consent", "T", None), "one", "zero_many", None),
        (("profile", "L", "display_name"), ("health_record", "L", "profile_id"), "one", "zero_many", GAP1),
        (("profile", "L", "display_name"), ("reminder", "L", "profile_id"), "one", "zero_many", GAP1),
        (("profile", "L", "display_name"), ("home_reading", "L", "profile_id"), "one", "zero_many", GAP1),
        (("profile", "R", "id"), ("report", "L", "profile_id"), "one", "zero_many", GAP2),
        (("report", "B", None), ("report_file", "T", None), "one", "one_many", None),
        (("report_file", "B", None), ("report_page", "T", None), "one", "one_many", None),
        (("report_page", "B", None), ("observation", "T", None), "zero_one", "zero_many", None),
        (("report", "L", "status"), ("observation", "L", "report_id"), "one", "zero_many", GAP2),
        (("report", "L", "status"), ("processing_job", "L", "report_id"), "one", "zero_many", GAP2),
        (("report", "L", "status"), ("report_grant", "L", "report_id"), "one", "zero_many", GAP2),
        (("report", "L", "status"), ("share_link", "R", "report_id"), "one", "zero_many", GAP2),
    ]
    return _er(712, place, rels, [
        "Also: report.uploaded_by, consent.user_id and report_grant.clinician_user_id refer to app_user;",
        "clinician_note.report_id to report; observation.test_id to lab_test (part b). Lines omitted for clarity.",
    ])


def er_b() -> Diagram:
    """Catalogue, knowledge and AI (15 tables)."""
    place = {"organ_system": (C0, 6), "lab_test": (C0, 104), "unit_conversion": (C0, 228),
             "reference_range": (C0, 326), "critical_limit": (C0, 440), "catalogue_revision": (C0, 580),
             "population_percentile": (C1, 6), "kb_document": (C1, 120), "kb_chunk": (C1, 218),
             "explanation_citation": (C1, 316), "trend_insight": (C1, 410),
             "explanation": (C2, 6), "feedback": (C2, 120), "report_question": (C2, 228), "safety_review": (C2, 356)}
    rels = [
        (("organ_system", "B", None), ("lab_test", "T", None), "one", "zero_many", None),
        (("lab_test", "B", None), ("unit_conversion", "T", None), "one", "zero_many", None),
        (("lab_test", "L", "id"), ("reference_range", "L", "test_id"), "one", "zero_many", LEFT),
        (("lab_test", "L", "id"), ("critical_limit", "L", "test_id"), "one", "zero_one", LEFT),
        (("lab_test", "R", "code"), ("population_percentile", "L", "test_id"), "one", "zero_many", GAP1),
        (("lab_test", "R", "code"), ("kb_chunk", "L", "test_id"), "zero_one", "zero_many", GAP1),
        (("lab_test", "R", "code"), ("trend_insight", "L", "test_id"), "one", "zero_many", GAP1),
        (("kb_document", "B", None), ("kb_chunk", "T", None), "one", "one_many", None),
        (("kb_chunk", "B", None), ("explanation_citation", "T", None), "one", "zero_many", None),
        (("explanation", "L", "language"), ("explanation_citation", "R", "explanation_id"), "one", "zero_many",
         GAP2),
        (("explanation", "B", None), ("feedback", "T", None), "one", "zero_many", None),
    ]
    return _er(712, place, rels, [
        "Also: explanation.report_id, report_question.report_id → report; trend_insight.profile_id → profile;",
        "feedback.user_id and safety_review.reviewer_id → app_user (part a). Legend: PK · FK · UQ unique.",
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
    """Requests, storage and the job queue."""
    d = page(PW, 500)
    W = 180
    X = [10, 211, 412]
    B = {}
    B["router"] = _cls(d, X[0], 6, W, "reports", [], ["+ upload_report()", "+ confirm_report()",
                                                      "+ delete_report()"], "cyan", "FastAPI router")
    B["ingest"] = _cls(d, X[1], 6, W, "services.ingest", [], ["+ sniff_mime(data)", "+ has_consent()",
                                                              "+ ingest_report()"], "blue", "module")
    B["queue"] = _cls(d, X[2], 6, W, "worker.queue", [], ["+ enqueue(report, stage)", "+ claim(): Job | None",
                                                          "+ fail(job, error)"], "green", "module")
    B["deps"] = _cls(d, X[0], 176, W, "api.deps", [], ["+ current_user()", "+ require_roles()",
                                                       "+ owned_report()"], "cyan", "module")
    B["storage"] = _cls(d, X[1], 176, W, "StorageBackend", [], ["+ put(key, data)", "+ get(key): bytes",
                                                                "+ delete(key)"], "green", "interface")
    B["worker"] = _cls(d, X[2], 176, W, "Worker", ["- sessions", "- handlers"], ["+ run_once(): bool",
                                                                             "+ run_forever(stop)"], "slate")
    B["live"] = _cls(d, X[0], 346, W, "LiveCatalogue", ["- revision", "- interpreter"],
                     ["+ get(session)"], "green")
    B["local"] = _cls(d, X[1], 346, W, "LocalVolumeStorage", ["- root: Path"], ["+ put / get / delete"], "green")
    B["handler"] = _cls(d, X[2], 346, W, "StageHandler", ["+ stage: JobStage"], ["+ handle(job, session)"],
                        "slate", "interface")

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
    d.arrow([R("router", 0.62), L("ingest", 0.62)], **assoc)
    d.arrow([R("ingest", 0.62), L("queue", 0.62)], **assoc)
    d.arrow([Bo("router"), T("deps")], **assoc)
    d.arrow([L("router", 0.3), (3, L("router", 0.3)[1]), (3, L("live", 0.3)[1]), L("live", 0.3)], **assoc)
    d.arrow([Bo("ingest"), T("storage")], **assoc)
    d.arrow([T("worker"), Bo("queue")], **assoc)
    d.arrow([Bo("worker"), T("handler")], color=INK_2, sw=1.2, head="open", tail="diamond")
    d.text(Bo("worker")[0] + 8, (Bo("worker")[1] + T("handler")[1]) / 2 + 4, "1..*", 9.5, 600, MUTED)
    d.arrow([T("local"), Bo("storage")], **real)
    d.legend(10, 480, [("line", INK_2, "association"), ("dash", INK_2, "realisation")])
    d.raw(f'<path d="M300,480 h22" stroke="{INK_2}" stroke-width="1.2" '
          f'marker-start="url(#{d._marker(INK_2, "diamond")})"/>')
    d.text(330, 484, "composition", 11, 400, INK_2)
    return d


def class_b() -> Diagram:
    """The pipeline stages and what each one uses."""
    d = page(PW, 690)
    pw, pad, gap = 144, 6, 18
    W = pw - 2 * pad
    xs = [3, 153, 303, 453]
    top = 112
    B = {}
    B["handler"] = _cls(d, 226, 4, 150, "StageHandler", [], ["+ handle(job)"], "slate", "interface")
    pk = [
        ("extraction", "teal", True, [
            ("extract", "ExtractionStage", [], ["+ handle(job)"], "slate", None),
            ("interp", "Interpreter", ["- matcher", "- converter"], ["+ interpret(row)"], "teal", None),
            ("matcher", "CatalogueMatcher", [], ["+ match(name)"], "teal", None),
            ("conf", "ConfidenceModel", [], ["+ predict(features)"], "teal", None),
            ("ocr", "OCREngine", [], ["+ read(image)"], "teal", "interface"),
            ("rapid", "RapidOCREngine", [], ["+ read(image)"], "teal", None),
        ]),
        ("analysis", "cyan", True, [
            ("analyse", "AnalysisStage", [], ["+ handle(job)"], "slate", None),
            ("svc_an", "services.analysis", [], ["+ analyse_profile()"], "cyan", "module"),
            ("status", "analysis.status", [], ["+ classify()"], "cyan", "module"),
            ("change", "analysis.change", [], ["+ rcv() · compare()"], "cyan", "module"),
            ("trend", "analysis.trend", [], ["+ theil_sen()", "+ mann_kendall()"], "cyan", "module"),
        ]),
        ("explanation", "purple", True, [
            ("explain", "ExplanationStage", [], ["+ handle(job)"], "slate", None),
            ("svc_ex", "services.explanation", [], ["+ explain_report()"], "purple", "module"),
            ("emb", "Embedder", [], ["+ embed(texts)"], "purple", "interface"),
            ("e5", "E5Embedder", [], ["+ embed(texts)"], "purple", None),
            ("llm", "LLMProvider", [], ["+ complete_json()"], "purple", "interface"),
            ("groq", "GroqProvider", [], ["+ complete_json()"], "purple", None),
            ("valid", "explain.validator", [], ["+ validate()"], "red", "module"),
        ]),
        ("on request (API)", "orange", False, [
            ("ask", "services.ask", [], ["+ answer_question()"], "orange", "module"),
            ("rules", "explain.ask", [], ["+ understand()"], "red", "module"),
            ("tts", "TTSProvider", [], ["+ synthesize()"], "orange", "interface"),
            ("eleven", "ElevenLabsProvider", [], ["+ synthesize()"], "orange", None),
        ]),
    ]
    for (pname, role, _, classes), x in zip(pk, xs):
        d.rect(x, top, pw, 556, fill=EDGE[role], stroke=EDGE[role], sw=1.2, rx=4, opacity=0.07)
        d.rect(x, top - 16, text_width(pname, 10.5, 700) + 16, 16, fill=TILE[role], stroke="none", rx=2)
        d.text(x + 8, top - 4, pname, 10.5, 700, PAPER)
        y = top + 12
        for key, name, attrs, methods, crole, stereo in classes:
            B[key] = _cls(d, x + pad, y, W, name, attrs, methods, crole, stereo)
            y += B[key][3] + gap
    real = dict(color=INK_2, sw=1.1, head="triangle", dash="5 3")
    use = dict(color=INK_2, sw=1.1, head="open", dash="4 3")
    hx, hy, hw, hh = B["handler"]
    bus = hy + hh + 15
    stages = [("extract", xs[0]), ("analyse", xs[1]), ("explain", xs[2])]
    tap = {k: x + pw * 0.8 for k, x in stages}            # right of each package tab
    for k, _ in stages:
        d.arrow([(tap[k], B[k][1]), (tap[k], bus)], color=INK_2, sw=1.1, head=None, dash="5 3")
    d.arrow([(tap["extract"], bus), (tap["explain"], bus)], color=INK_2, sw=1.1, head=None, dash="5 3")
    d.arrow([(hx + hw / 2, bus), (hx + hw / 2, hy + hh)], **real)
    for s, c in (("extract", "interp"), ("analyse", "svc_an"), ("explain", "svc_ex"), ("ask", "rules")):
        x, y, w, h = B[s]
        d.arrow([(x + w / 2, y + h), (x + w / 2, B[c][1])], **use)
    for impl, iface in (("rapid", "ocr"), ("e5", "emb"), ("groq", "llm"), ("eleven", "tts")):
        x, y, w, h = B[impl]
        d.arrow([(x + w / 2, y), (x + w / 2, B[iface][1] + B[iface][3])], **real)
    d.text(3, 684, "Each stage uses the classes in its package; dashed triangles mark implementations.",
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
            label = f"{r['e']:%d %b}"
            if cx + 9 + text_width(label, 9.5, 700) > LW:
                d.text(cx - 9, y + 11.5, label, 9.5, 700, TILE["orange"], "end")
            else:
                d.text(cx + 9, y + 11.5, label, 9.5, 700, TILE["orange"])
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
        ("Elaboration", "10 – 16 Aug", "cyan", ["Test catalogue (70 tests)", "Synthetic report generator",
                                               "3D body spike (procedural)", "Knowledge sources + licences"],
         "risks retired"),
        ("Construction", "17 Aug – 20 Sep", "blue", ["S2–S3 extraction + review", "S4 analytics engine",
                                                      "S5 grounded explanations", "S6 body map + accounts"],
         "M1 30 Aug · M2 20 Sep"),
        ("Transition", "21 – 30 Sep", "green", ["S7 sharing, care, Ask Nabz", "Console + offline mode",
                                                    "Usability plan, review packet", "Report, slides, rehearsal"],
         "M3 · demo ready"),
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
        "Doing": (48, 62, [["PDF arrives on", "WhatsApp"], ["Uploads the PDF", "to Nabz"], ["Fixes one misread", "value"],
                           ["Taps the liver;", "plays Odia audio"], ["Shares with the", "doctor; asks"],
                           ["Replays the", "story"]]),
        "Pain points": (262, 54, [["20+ unfamiliar", "abbreviations"], ["skewed, shadowed", "photos"],
                                  ["misread values", "would mislead"], ["alarming, generic", "search results"],
                                  ["5-minute visit;", "forgets questions"], ["different labs,", "different units"]]),
        "How Nabz helps": (324, 54, [["body map shows", "what matters"], ["text layer or", "OCR, then review"],
                                     ["human review of", "weak rows"], ["grounded, checked,", "in Odia"],
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
