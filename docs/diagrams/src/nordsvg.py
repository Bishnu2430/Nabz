"""nordsvg — a tiny, dependency-free SVG toolkit for the Nabz documentation.

Every diagram in docs/diagrams is generated with these primitives so that the
whole set shares one visual language: the Nord palette, grouped boundaries with
a corner tag, icon tiles with labels underneath, numbered step badges and
orthogonal connectors. Layout conventions are inspired by cloud architecture
diagrams; no third-party icons or branding are used — all glyphs are drawn here.
"""

from __future__ import annotations

import math
from html import escape
from pathlib import Path

# --- Palette -----------------------------------------------------------------
# Nord base colours (https://www.nordtheme.com) plus slightly deeper "tile"
# variants so white glyphs keep enough contrast.
INK = "#2E3440"        # nord0  — primary text
INK_2 = "#4C566A"      # nord3  — secondary text, default connectors
MUTED = "#6B7385"      # captions
LINE = "#D8DEE9"       # nord4  — hairlines, grid
PAPER = "#FFFFFF"
SNOW = "#ECEFF4"       # nord6  — subtle fills
SNOW_2 = "#E5E9F0"     # nord5

FROST_TEAL = "#8FBCBB"
FROST_CYAN = "#88C0D0"
FROST_BLUE = "#81A1C1"
FROST_DEEP = "#5E81AC"
RED = "#BF616A"
ORANGE = "#D08770"
YELLOW = "#EBCB8B"
GREEN = "#A3BE8C"
PURPLE = "#B48EAD"

# Tile colours (deeper variants) keyed by role.
TILE = {
    "teal": "#5E9C9A",
    "cyan": "#4F97AE",
    "blue": FROST_DEEP,
    "slate": INK_2,
    "green": "#6E9A5B",
    "purple": "#8E6D95",
    "orange": "#C06B47",
    "red": RED,
    "yellow": "#C99A3A",
}
# Boundary colours keyed by the same roles.
EDGE = {
    "teal": FROST_TEAL,
    "cyan": FROST_CYAN,
    "blue": FROST_DEEP,
    "slate": INK_2,
    "green": GREEN,
    "purple": PURPLE,
    "orange": ORANGE,
    "red": RED,
    "yellow": YELLOW,
}

FONT = "Inter, 'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', Consolas, 'Courier New', monospace"

# --- Icons (24×24 line glyphs, drawn for this project) ----------------------
ICONS: dict[str, str] = {
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"/>',
    "users": '<circle cx="9" cy="8" r="3.4"/><path d="M2.5 20c0-3.8 2.9-6 6.5-6s6.5 2.2 6.5 6"/>'
             '<path d="M15.5 4.8a3.4 3.4 0 0 1 0 6.5M18 14.3c2.1.7 3.5 2.6 3.5 5.7"/>',
    "doctor": '<circle cx="12" cy="6.5" r="3.5"/><path d="M5 21v-2.5C5 15 8 13 12 13s7 2 7 5.5V21"/>'
              '<path d="M9.5 13.5v3a2.5 2.5 0 0 0 5 0v-3"/>',
    "admin": '<circle cx="10" cy="8" r="3.8"/><path d="M3 21c0-4 3.1-6.5 7-6.5 1.2 0 2.3.2 3.3.7"/>'
             '<circle cx="18" cy="17" r="2.2"/><path d="M18 12.8v1.6M18 19.6v1.6M13.8 17h1.6M20.6 17h1.6"/>',
    "browser": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18"/>'
               '<path d="M6 6.5h.01M8.5 6.5h.01"/>',
    "phone": '<rect x="7" y="2.5" width="10" height="19" rx="2"/><path d="M11 18.5h2"/>',
    "server": '<rect x="3.5" y="4" width="17" height="7" rx="1.5"/><rect x="3.5" y="13" width="17" height="7" rx="1.5"/>'
              '<path d="M7 7.5h.01M7 16.5h.01M11 7.5h6M11 16.5h6"/>',
    "api": '<path d="M8 7l-5 5 5 5M16 7l5 5-5 5M13.5 5l-3 14"/>',
    "gear": '<circle cx="12" cy="12" r="3.2"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3'
            'M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1"/>',
    "database": '<ellipse cx="12" cy="5.5" rx="7" ry="2.5"/><path d="M5 5.5v13c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5v-13"/>'
                '<path d="M5 12c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5"/>',
    "vector": '<path d="M6 6l6 3 6-4M6 6l1 9 8 2 4-5-1-7M12 9l3 8M12 9l-5 6"/>'
              '<circle cx="6" cy="6" r="1.4"/><circle cx="12" cy="9" r="1.4"/><circle cx="18" cy="5" r="1.4"/>'
              '<circle cx="7" cy="15" r="1.4"/><circle cx="15" cy="17" r="1.4"/><circle cx="19" cy="12" r="1.4"/>',
    "disk": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 13h18"/><path d="M16.5 16h.01M13.5 16h.01"/>',
    "sparkle": '<path d="M11 3l1.8 5.2L18 10l-5.2 1.8L11 17l-1.8-5.2L4 10l5.2-1.8z"/>'
               '<path d="M18.5 15l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z"/>',
    "scan": '<path d="M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3"/>'
            '<path d="M8 9.5h8M8 12.5h8M8 15.5h5"/>',
    "document": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/><path d="M9 12h6M9 15.5h6M9 8.5h2"/>',
    "speaker": '<path d="M4 9h4l5-4v14l-5-4H4z"/><path d="M16.5 8.5a5 5 0 0 1 0 7M19 6a8.5 8.5 0 0 1 0 12"/>',
    "lock": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/><path d="M12 15v2"/>',
    "shield": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
    "chart": '<path d="M4 4v16h16"/><path d="M7.5 15l4-4.5 3 3L19.5 7"/>',
    "body": '<circle cx="12" cy="4.6" r="2.3"/><path d="M12 7.5v7M6.5 10.5h11M12 14.5l-3.5 6.5M12 14.5l3.5 6.5"/>',
    "queue": '<path d="M9 6h11M9 12h11M9 18h11"/><path d="M4.5 6h.01M4.5 12h.01M4.5 18h.01"/>',
    "cube": '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M4 7.5l8 4.5 8-4.5M12 12v9"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/>',
    "cloud": '<path d="M7 18.5h10.5a4 4 0 0 0 .3-8A6 6 0 0 0 6.2 11 3.8 3.8 0 0 0 7 18.5z"/>',
    "key": '<circle cx="8" cy="15" r="4"/><path d="M11 12l8.5-8.5M16 7l2.5 2.5M13.5 9.5l2 2"/>',
    "book": '<path d="M5 4.5A1.5 1.5 0 0 1 6.5 3H19v15H6.5A1.5 1.5 0 0 0 5 19.5z"/><path d="M5 19.5A1.5 1.5 0 0 0 6.5 21H19v-3"/>'
            '<path d="M9 7.5h6M9 11h4"/>',
    "alert": '<path d="M12 3.5l9 16H3z"/><path d="M12 10v4M12 17h.01"/>',
    "laptop": '<rect x="4" y="5" width="16" height="10.5" rx="1.2"/><path d="M2 19h20"/>',
    "network": '<circle cx="12" cy="5" r="2"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="19" r="2"/>'
               '<path d="M12 7v5M12 12l-6 5.3M12 12l6 5.3"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.7 2.7L16.5 9"/>',
    "translate": '<path d="M4 5h9M8.5 3v2M6 5c0 4 3 7 6.5 8M11 5c-.7 4-3.4 7-6.5 8.5"/>'
                 '<path d="M13 21l3.5-9 3.5 9M14.3 18h4.4"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21"/>',
    "flag": '<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>',
    "folder": '<path d="M3 6.5A1.5 1.5 0 0 1 4.5 5H9l2 2.5h8.5A1.5 1.5 0 0 1 21 9v9.5a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 18.5z"/>',
    "calendar": '<rect x="3.5" y="5" width="17" height="15.5" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
    "rule": '<path d="M4 6h10M4 12h16M4 18h7"/><path d="M17 4l3 3-3 3"/>',
}


def icon(name: str, x: float, y: float, size: float = 24, color: str = PAPER, width: float = 1.8) -> str:
    """Place a 24×24 glyph scaled to `size` with its top-left at (x, y)."""
    s = size / 24
    return (
        f'<g transform="translate({x:.1f},{y:.1f}) scale({s:.4f})" fill="none" stroke="{color}" '
        f'stroke-width="{width / s:.2f}" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</g>'
    )


# --- Text helpers ------------------------------------------------------------
def text_width(s: str, size: float, weight: int = 400, mono: bool = False) -> float:
    """Rough advance width — good enough for layout."""
    if mono:
        return len(s) * size * 0.6
    factor = 0.56 if weight < 600 else 0.6
    narrow = sum(1 for c in s if c in "il.,:;'|!()[] ")
    return (len(s) - narrow * 0.55) * size * factor


class Diagram:
    """An SVG canvas with helpers for the Nabz diagram language."""

    def __init__(self, width: int, height: int, title: str | None = None,
                 subtitle: str | None = None, margin: int = 32, physical: bool = False):
        """physical=True writes width/height in centimetres (1 px = 1/96 in) so that
        Word and LibreOffice insert the figure at exactly its designed print size."""
        self.w, self.h, self.m, self.physical = width, height, margin, physical
        self.parts: list[str] = []
        self.markers: dict[str, str] = {}
        self.parts.append(f'<rect width="{width}" height="{height}" fill="{PAPER}"/>')
        if title:
            self.text(margin, margin + 6, title, 20, 700, INK)
        if subtitle:
            self.text(margin, margin + 28, subtitle, 12.5, 400, MUTED)

    # -- low level ------------------------------------------------------------
    def raw(self, svg: str) -> None:
        self.parts.append(svg)

    def text(self, x: float, y: float, s: str, size: float = 12.5, weight: int = 400,
             color: str = INK, anchor: str = "start", italic: bool = False,
             family: str | None = None) -> None:
        style = ' font-style="italic"' if italic else ""
        fam = f' font-family="{family}"' if family else ""
        self.parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" '
            f'fill="{color}" text-anchor="{anchor}"{style}{fam}>{escape(s)}</text>'
        )

    def lines(self, x: float, y: float, rows: list[str], size: float = 12, weight: int = 400,
              color: str = INK, anchor: str = "start", leading: float = 1.35) -> float:
        """Draw several lines of text; returns the y just below the block."""
        for i, row in enumerate(rows):
            self.text(x, y + i * size * leading, row, size, weight, color, anchor)
        return y + len(rows) * size * leading

    def rect(self, x: float, y: float, w: float, h: float, fill: str = PAPER, stroke: str = LINE,
             sw: float = 1.2, rx: float = 6, dash: str | None = None, opacity: float = 1.0) -> None:
        d = f' stroke-dasharray="{dash}"' if dash else ""
        op = f' fill-opacity="{opacity}"' if opacity < 1 else ""
        self.parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
            f'fill="{fill}"{op} stroke="{stroke}" stroke-width="{sw}"{d}/>'
        )

    def circle(self, cx: float, cy: float, r: float, fill: str, stroke: str = "none", sw: float = 1) -> None:
        self.parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str = LINE, sw: float = 1,
             dash: str | None = None) -> None:
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="{sw}"{d}/>')

    # -- markers ----------------------------------------------------------------
    def _marker(self, color: str, kind: str = "arrow") -> str:
        mid = f"m-{kind}-{color.strip('#')}"
        if mid not in self.markers:
            if kind == "arrow":
                shape = f'<path d="M0,0 L10,5 L0,10 z" fill="{color}"/>'
                self.markers[mid] = (
                    f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
                    f'markerHeight="7" orient="auto-start-reverse">{shape}</marker>'
                )
            elif kind == "open":  # UML open arrowhead
                shape = f'<path d="M1,1 L10,5 L1,9" fill="none" stroke="{color}" stroke-width="1.4"/>'
                self.markers[mid] = (
                    f'<marker id="{mid}" viewBox="0 0 11 10" refX="10" refY="5" markerWidth="9" '
                    f'markerHeight="9" orient="auto-start-reverse">{shape}</marker>'
                )
            elif kind == "triangle":  # UML generalisation / realisation
                shape = f'<path d="M1,1 L12,6.5 L1,12 z" fill="{PAPER}" stroke="{color}" stroke-width="1.3"/>'
                self.markers[mid] = (
                    f'<marker id="{mid}" viewBox="0 0 13 13" refX="12" refY="6.5" markerWidth="12" '
                    f'markerHeight="12" orient="auto-start-reverse" markerUnits="userSpaceOnUse">{shape}</marker>'
                )
            elif kind == "diamond":  # UML composition
                shape = f'<path d="M1,6 L7,1 L13,6 L7,11 z" fill="{color}"/>'
                self.markers[mid] = (
                    f'<marker id="{mid}" viewBox="0 0 14 12" refX="13" refY="6" markerWidth="13" '
                    f'markerHeight="11" orient="auto-start-reverse" markerUnits="userSpaceOnUse">{shape}</marker>'
                )
        return mid

    # -- connectors -------------------------------------------------------------
    @staticmethod
    def _rounded(points: list[tuple[float, float]], r: float = 7) -> str:
        if len(points) == 2:
            (x1, y1), (x2, y2) = points
            return f"M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}"
        d = f"M{points[0][0]:.1f},{points[0][1]:.1f}"
        for i in range(1, len(points) - 1):
            px, py = points[i - 1]
            cx, cy = points[i]
            nx, ny = points[i + 1]
            l1 = math.hypot(cx - px, cy - py)
            l2 = math.hypot(nx - cx, ny - cy)
            rr = min(r, l1 / 2, l2 / 2)
            ax, ay = cx - (cx - px) / l1 * rr, cy - (cy - py) / l1 * rr
            bx, by = cx + (nx - cx) / l2 * rr, cy + (ny - cy) / l2 * rr
            d += f" L{ax:.1f},{ay:.1f} Q{cx:.1f},{cy:.1f} {bx:.1f},{by:.1f}"
        d += f" L{points[-1][0]:.1f},{points[-1][1]:.1f}"
        return d

    def arrow(self, points: list[tuple[float, float]], color: str = INK_2, sw: float = 1.4,
              dash: str | None = None, head: str = "arrow", tail: str | None = None,
              label: str | None = None, label_at: tuple[float, float] | None = None,
              label_color: str | None = None) -> None:
        """Orthogonal connector. `head`/`tail`: arrow, open, triangle, diamond or None."""
        attrs = f'fill="none" stroke="{color}" stroke-width="{sw}" stroke-linejoin="round"'
        if dash:
            attrs += f' stroke-dasharray="{dash}"'
        if head:
            attrs += f' marker-end="url(#{self._marker(color, head)})"'
        if tail:
            attrs += f' marker-start="url(#{self._marker(color, tail)})"'
        self.parts.append(f'<path d="{self._rounded(points)}" {attrs}/>')
        if label:
            if label_at is None:
                # midpoint of the longest segment
                best = max(range(len(points) - 1),
                           key=lambda i: math.hypot(points[i + 1][0] - points[i][0], points[i + 1][1] - points[i][1]))
                (x1, y1), (x2, y2) = points[best], points[best + 1]
                label_at = ((x1 + x2) / 2, (y1 + y2) / 2)
            self.pill(label_at[0], label_at[1], label, label_color or INK_2)

    def pill(self, cx: float, cy: float, s: str, color: str = INK_2, size: float = 10.5) -> None:
        w = text_width(s, size) + 12
        self.rect(cx - w / 2, cy - 9, w, 18, fill=PAPER, stroke="none", rx=9)
        self.text(cx, cy + 3.7, s, size, 500, color, "middle")

    def step(self, cx: float, cy: float, n: int | str, color: str = INK) -> None:
        """Numbered step badge."""
        self.circle(cx, cy, 11, color)
        self.text(cx, cy + 4, str(n), 11, 700, PAPER, "middle")

    # -- building blocks --------------------------------------------------------
    def group(self, x: float, y: float, w: float, h: float, label: str, role: str = "slate",
              glyph: str | None = None, dashed: bool = False, tint: bool = True,
              sublabel: str | None = None) -> None:
        """Boundary box with a coloured corner tag (icon square + label)."""
        edge = EDGE[role]
        self.rect(x, y, w, h, fill=edge if tint else PAPER, stroke=edge, sw=1.5, rx=4,
                  dash="6 4" if dashed else None, opacity=0.06 if tint else 1)
        if glyph:
            self.rect(x, y, 28, 28, fill=TILE[role], stroke="none", rx=0)
            self.raw(icon(glyph, x + 5, y + 5, 18))
            tx = x + 38
        else:
            tx = x + 12
        self.text(tx, y + 18.5, label, 12.5, 600, INK)
        if sublabel:
            self.text(tx + text_width(label, 12.5, 600) + 10, y + 18.5, sublabel, 11, 400, MUTED)

    def node(self, cx: float, cy: float, label: str, glyph: str, role: str = "blue",
             sub: str | list[str] | None = None, size: int = 52) -> None:
        """Icon tile centred on (cx, cy) with a label underneath."""
        x, y = cx - size / 2, cy - size / 2
        self.rect(x, y, size, size, fill=TILE[role], stroke="none", rx=8)
        g = size * 0.58
        self.raw(icon(glyph, cx - g / 2, cy - g / 2, g, width=1.7))
        self.text(cx, y + size + 17, label, 12.5, 600, INK, "middle")
        if sub:
            rows = [sub] if isinstance(sub, str) else sub
            self.lines(cx, y + size + 32, rows, 10.8, 400, MUTED, "middle", 1.3)

    def card(self, x: float, y: float, w: float, h: float, title: str, rows: list[str] | None = None,
             role: str = "blue", glyph: str | None = None, fill: str = PAPER, title_size: float = 12.5,
             row_size: float = 11, accent: bool = True) -> None:
        """Rounded card with a coloured left accent, optional glyph, title and body rows."""
        self.rect(x, y, w, h, fill=fill, stroke=LINE, sw=1.1, rx=6)
        if accent:
            self.rect(x + 1.5, y + 10, 3.5, h - 20, fill=TILE[role], stroke="none", rx=1.75)
        tx = x + 16
        if glyph:
            self.rect(x + 14, y + 12, 26, 26, fill=TILE[role], stroke="none", rx=5)
            self.raw(icon(glyph, x + 18, y + 16, 18))
            tx = x + 50
        self.text(tx, y + 30 if glyph else y + 24, title, title_size, 650, INK)
        if rows:
            ry = y + (58 if glyph else 44)
            self.lines(x + 16, ry, rows, row_size, 400, INK_2, "start", 1.42)

    def legend(self, x: float, y: float, items: list[tuple[str, str, str]]) -> None:
        """items: (kind, colour, label) where kind is 'line', 'dash', 'box' or 'dot'."""
        cx = x
        for kind, color, label in items:
            if kind == "line":
                self.arrow([(cx, y), (cx + 26, y)], color=color)
            elif kind == "dash":
                self.arrow([(cx, y), (cx + 26, y)], color=color, dash="5 4")
            elif kind == "box":
                self.rect(cx, y - 7, 26, 14, fill=color, stroke="none", rx=3)
            elif kind == "dot":
                self.circle(cx + 13, y, 6, color)
            self.text(cx + 34, y + 4, label, 11, 400, INK_2)
            cx += 34 + text_width(label, 11) + 26

    def footer(self, s: str) -> None:
        self.text(self.m, self.h - 16, s, 10.5, 400, MUTED)

    # -- output -----------------------------------------------------------------
    def svg(self) -> str:
        defs = f"<defs>{''.join(self.markers.values())}</defs>" if self.markers else ""
        body = "\n".join(self.parts)
        if self.physical:
            w, h = f"{self.w * 2.54 / 96:.2f}cm", f"{self.h * 2.54 / 96:.2f}cm"
        else:
            w, h = self.w, self.h
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {self.w} {self.h}" role="img">\n{defs}\n'
            f'<g font-family="{FONT}">\n{body}\n</g>\n</svg>\n'
        )

    def save(self, path: Path) -> None:
        path.write_text(self.svg(), encoding="utf-8", newline="\n")
