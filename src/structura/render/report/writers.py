"""Write a Report in the format its file suffix names. PDF and ODT need Qt's document engine and are written
by services.report_documents; this module handles the formats that are plain text."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .html_writer import to_html
from .model import Report
from .text_writers import save_thumbnail, to_csv, to_json, to_markdown, to_text

FORMATS = {  # suffix → (name, description) in the order Save dialogs list them
    ".pdf": ("PDF", "a printable document"),
    ".html": ("HTML", "a single web page with the images inlined"),
    ".md": ("Markdown", "for notes, wikis and READMEs (a preview image is saved beside it)"),
    ".txt": ("Plain text", "aligned columns"),
    ".json": ("JSON", "every value, machine-readable"),
    ".csv": ("CSV", "one row per value, for spreadsheets"),
    ".odt": ("OpenDocument text", "for LibreOffice and Word"),
}
QT_FORMATS = (".pdf", ".odt")
TEXT: dict[str, Callable[[Report], str]] = {".html": to_html, ".txt": to_text, ".json": to_json, ".csv": to_csv}


def report_filters() -> list[str]:
    """File-dialog filters, one per format."""
    return [f"{name} (*{suffix})" for suffix, (name, _) in FORMATS.items()]


def write_text_report(report: Report, path: Path) -> list[Path]:
    """Write ``report`` as text, Markdown, HTML, JSON or CSV; returns the files written."""
    suffix = path.suffix.lower()
    if suffix == ".md":
        preview = save_thumbnail(report, path.with_name(f"{path.stem}-preview.png"))
        path.write_text(to_markdown(report, preview.name if preview else None), encoding="utf-8")
        return [path, *([preview] if preview else [])]
    if suffix not in TEXT:
        raise ValueError(f"unsupported report format '{suffix}' (use one of {', '.join(FORMATS)})")
    path.write_text(TEXT[suffix](report), encoding="utf-8")
    return [path]
