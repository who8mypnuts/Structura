"""Plain text, Markdown, JSON and CSV renderings of a Report."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .model import Report, Section, Table

BARS = " ▁▂▃▄▅▆▇█"


def sparkline(report: Report, width: int = 32) -> str:
    """The luminance histogram as block characters (dark tones on the left)."""
    if report.histogram is None:
        return ""
    lum = report.histogram[:, 3]
    lum = lum.reshape(width, -1).max(axis=1) if lum.size % width == 0 else lum
    return "".join(BARS[round(v * (len(BARS) - 1))] for v in lum / max(float(lum.max()), 1e-12))


def _table_lines(table: Table, indent: str = "  ") -> list[str]:
    widths = [max(len(c), *(len(r[i]) for r in table.rows)) for i, c in enumerate(table.columns)]
    line = indent + "  ".join(c.ljust(w) for c, w in zip(table.columns, widths, strict=True))
    rule = indent + "  ".join("─" * w for w in widths)
    body = [indent + "  ".join(v.ljust(w) for v, w in zip(r, widths, strict=True)) for r in table.rows]
    return [f"{indent}{table.title}", line, rule, *body]


def _section_lines(section: Section) -> list[str]:
    width = max((len(r.label) for r in section.rows), default=0) + 2
    lines = [section.title.upper(), "─" * len(section.title)]
    for r in section.rows:
        lines.append(f"  {(r.label + ' ').ljust(width, '.')} {r.text}")
        if r.note:
            lines.append(f"  {' ' * width} ({r.note})")
    for table in section.tables:
        lines += ["", *_table_lines(table)]
    return [*lines, ""]


def to_text(report: Report) -> str:
    lines = [report.title, report.subtitle, "═" * max(len(report.title), len(report.subtitle)), ""]
    lines += ["   ".join(f"{label}: {value}" for label, value in report.highlights), ""]
    if report.histogram is not None:
        lines += [f"Luminance histogram  [{sparkline(report)}]", ""]
    if report.palette:
        lines += ["Palette  " + "  ".join(f"{s.hex} {100 * s.share:.1f}%" for s in report.palette), ""]
    for section in report.sections:
        lines += _section_lines(section)
    return "\n".join(lines)


def _md_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _md_section(section: Section) -> list[str]:
    lines = [f"## {section.title}", "", "| Property | Value |", "|---|---|"]
    for r in section.rows:
        note = f"<br><sub>{_md_cell(r.note)}</sub>" if r.note else ""
        lines.append(f"| {_md_cell(r.label)} | {_md_cell(r.text)}{note} |")
    for table in section.tables:
        lines += ["", f"**{table.title}**", "", "| " + " | ".join(table.columns) + " |",
                  "|" + "---|" * len(table.columns)]  # fmt: skip
        lines += ["| " + " | ".join(_md_cell(v) for v in r) + " |" for r in table.rows]
    return [*lines, ""]


def to_markdown(report: Report, preview: str | None = None) -> str:
    """``preview``: a relative image path to show at the top (the writer saves the thumbnail there)."""
    lines = [f"# {report.title}", "", f"*{report.subtitle}*", ""]
    if preview:
        lines += [f"![Render preview]({preview})", ""]
    labels, values = zip(*report.highlights, strict=True) if report.highlights else ((), ())
    lines += ["| " + " | ".join(labels) + " |", "|" + "---|" * len(labels), "| " + " | ".join(values) + " |", ""]
    if report.histogram is not None:
        lines += [f"**Luminance histogram** `{sparkline(report)}`", ""]
    if report.palette:
        lines += ["**Palette** " + " · ".join(f"`{s.hex}` {100 * s.share:.1f} %" for s in report.palette), ""]
    for section in report.sections:
        lines += _md_section(section)
    return "\n".join(lines)


def _plain(value: Any) -> Any:
    """JSON-safe: numpy scalars and arrays to Python, non-finite floats to strings."""
    if isinstance(value, np.generic | np.ndarray):
        return _plain(value.tolist())
    if isinstance(value, list | tuple):
        return [_plain(v) for v in value]
    if isinstance(value, float) and not np.isfinite(value):
        return str(value)
    return value


def _section_data(s: Section) -> dict[str, Any]:
    tables = [{"title": t.title, "columns": list(t.columns), "rows": [list(r) for r in t.rows]} for t in s.tables]
    return {"title": s.title, "values": {r.label: _plain(r.value) for r in s.rows}, "tables": tables}


def to_json(report: Report) -> str:
    data = {
        "title": report.title,
        "created": report.created,
        "highlights": dict(report.highlights),
        "sections": {s.key: _section_data(s) for s in report.sections},
        "palette": [{"hex": s.hex, "share": s.share} for s in report.palette],
        "histogram": _plain(report.histogram) if report.histogram is not None else None,
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def to_csv(report: Report) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["section", "property", "value", "raw", "note"])
    for s in report.sections:
        for r in s.rows:
            writer.writerow([s.title, r.label, r.text, json.dumps(_plain(r.value), ensure_ascii=False), r.note])
    return out.getvalue()


def save_thumbnail(report: Report, path: Path) -> Path | None:
    if report.thumbnail is None:
        return None
    Image.fromarray(report.thumbnail).save(path)
    return path
