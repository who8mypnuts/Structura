"""A self-contained HTML report: one file, images inlined, readable in a browser and by Qt's document engine
(which turns the same HTML into PDF and ODT, so the markup sticks to tables and simple CSS)."""

from __future__ import annotations

import base64
import html
import io

import numpy as np
from PIL import Image, ImageDraw

from .model import Report, Section, Table

CHANNELS = (("#e05252", 0), ("#4caf50", 1), ("#4f7fe0", 2))
# Qt's engine stops reading at media queries with features, so browser-only layout comes last.
ALT, HEAD, CARD = "#f3f5f9", "#e5e9f0", "#eceff4"  # attributes as well as CSS: Qt's engine reads those
TABLE = 'width="100%" cellspacing="0" cellpadding="5" border="0"'
CSS = """
body { font-family: 'Inter', 'Segoe UI', Helvetica, Arial, sans-serif; color: #1e2430; background: #ffffff;
       font-size: 10pt; }
h1 { font-size: 20pt; margin: 0 0 2px 0; color: #1e2430; }
h2 { font-size: 13pt; margin: 22px 0 6px 0; padding-bottom: 3px; border-bottom: 2px solid #5e81ac; color: #2e3440; }
.subtitle { color: #6b7385; margin-bottom: 14px; }
table { border-collapse: collapse; }
td, th { vertical-align: top; text-align: left; }
td.label { color: #4c566a; }
.mono { font-family: 'JetBrains Mono', 'Cascadia Mono', 'DejaVu Sans Mono', Consolas, monospace; font-size: 9pt; }
.note { color: #7b8496; font-size: 8pt; }
.card-label { color: #6b7385; font-size: 7pt; text-transform: uppercase; }
.card-value { font-size: 12pt; font-weight: 600; color: #2e3440; }
.swatch { font-size: 14pt; }
@media (prefers-color-scheme: dark) {
  body { background: #1f232b; color: #e5e9f0; } h1, h2, .card-value { color: #eceff4; }
  td.alt { background: #262b35; } th, td.card { background: #2e3440; } td.label { color: #b8c0cf; }
}
@media screen and (min-width: 0px) { body { margin: 24px auto; max-width: 980px; padding: 0 16px; } }
"""


def png_data_uri(image: np.ndarray) -> str:
    buffer = io.BytesIO()
    Image.fromarray(image).save(buffer, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def histogram_image(histogram: np.ndarray, width: int = 512, height: int = 120) -> np.ndarray:
    """R, G, B and luminance histograms drawn as overlapping outlines on white (an image, so PDF shows it)."""
    canvas = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(canvas)
    bins = histogram.shape[0]
    xs = np.linspace(0, width - 1, bins)
    lum = [(float(x), height - 1 - float(v) * (height - 6)) for x, v in zip(xs, histogram[:, 3], strict=True)]
    draw.polygon([(0, height - 1), *lum, (width - 1, height - 1)], fill="#d8dee9")
    for colour, channel in CHANNELS:
        points = [(float(x), height - 1 - float(v) * (height - 6)) for x, v in zip(xs, histogram[:, channel],
                                                                                   strict=True)]  # fmt: skip
        draw.line(points, fill=colour, width=2)
    return np.asarray(canvas)


def _cell(text: str, alt: bool, extra: str = "") -> str:
    shade = f' class="alt" bgcolor="{ALT}"' if alt else ""
    return f"<td{shade}{extra}>{text}</td>"


def _props(section: Section) -> str:
    rows = []
    for n, r in enumerate(section.rows):
        note = f'<br><span class="note">{html.escape(r.note)}</span>' if r.note else ""
        label = _cell(html.escape(r.label), n % 2 == 1, ' width="34%"').replace("<td", '<td class="label"', 1)
        value = _cell(f'<span class="mono">{html.escape(r.text)}</span>{note}', n % 2 == 1)
        rows.append(f"<tr>{label}{value}</tr>")
    return f"<table {TABLE}>{''.join(rows)}</table>" if rows else ""


def _grid(table: Table) -> str:
    head = "".join(f'<th bgcolor="{HEAD}">{html.escape(c)}</th>' for c in table.columns)
    body = "".join("<tr>" + "".join(_cell(html.escape(v), n % 2 == 1) for v in r) + "</tr>"
                   for n, r in enumerate(table.rows))  # fmt: skip
    return f"<p><b>{html.escape(table.title)}</b></p><table {TABLE}><tr>{head}</tr>{body}</table>"


def _cards(report: Report) -> str:
    width = 100 // max(1, len(report.highlights))
    cells = "".join(f'<td class="card" bgcolor="{CARD}" align="center" width="{width}%">'
                    f'<span class="card-label">{html.escape(label)}</span><br>'
                    f'<span class="card-value">{html.escape(value)}</span></td>'
                    for label, value in report.highlights)  # fmt: skip
    return f'<table width="100%" cellspacing="4" cellpadding="8" border="0"><tr>{cells}</tr></table>'


def _palette(report: Report) -> str:
    width = 100 // max(1, len(report.palette))
    items = "".join(f'<td align="center" width="{width}%"><span class="swatch" style="color:{s.hex}">■■</span><br>'
                    f'<span class="mono">{s.hex}</span><br><span class="note">{100 * s.share:.1f} %</span></td>'
                    for s in report.palette)  # fmt: skip
    table = f'<table width="100%" cellspacing="0" cellpadding="2" border="0"><tr>{items}</tr></table>'
    return f"<h2>Palette</h2><p class='note'>The most common colours of the saved image.</p>{table}" if items else ""


def _pictures(report: Report) -> str:
    parts = []
    if report.thumbnail is not None:
        w = report.thumbnail.shape[1]
        parts.append(f'<p><img src="{png_data_uri(report.thumbnail)}" width="{min(w, 640)}" alt="Render"></p>')
    if report.histogram is not None:
        parts.append("<h2>Histogram</h2><p class='note'>Red, green, blue and (filled) luminance of the saved"
                     " image (square-root scale), dark tones on the left.</p>"
                     f'<p><img src="{png_data_uri(histogram_image(report.histogram))}" width="512"></p>')  # fmt: skip
    return "".join(parts)


def to_html(report: Report) -> str:
    body = [f"<h1>{html.escape(report.title)}</h1>", f'<div class="subtitle">{html.escape(report.subtitle)}</div>',
            _cards(report), _pictures(report), _palette(report)]  # fmt: skip
    for section in report.sections:
        body.append(f"<h2>{html.escape(section.title)}</h2>{_props(section)}")
        body += [_grid(t) for t in section.tables]
    return (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>{html.escape(report.title)}</title>'
            f'<meta name="viewport" content="width=device-width, initial-scale=1"><style>{CSS}</style></head>'
            f'<body>{"".join(body)}</body></html>')  # fmt: skip
