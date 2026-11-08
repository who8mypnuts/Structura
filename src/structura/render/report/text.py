"""Render the report's data (data.py) to text formats (docs/09 §11): Markdown, plain text and HTML share one
Jinja2 template each; JSON is the data class as-is, for other tools to read."""

from __future__ import annotations

import dataclasses
import json
from functools import cache
from pathlib import Path
from typing import Any

import jinja2

from .data import ReportData

TEMPLATES = Path(__file__).resolve().parent / "templates"


@cache
def _environment() -> jinja2.Environment:
    return jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATES), keep_trailing_newline=True,
                              trim_blocks=True, lstrip_blocks=True, undefined=jinja2.StrictUndefined)  # fmt: skip


def to_markdown(data: ReportData) -> str:
    return _environment().get_template("report.md.j2").render(d=data)


def to_text(data: ReportData) -> str:
    return _environment().get_template("report.txt.j2").render(d=data)


def to_html(data: ReportData) -> str:
    env = _environment()
    env.autoescape = True
    try:
        return env.get_template("report.html.j2").render(d=data)
    finally:
        env.autoescape = False


def to_json(data: ReportData) -> str:
    return json.dumps(dataclasses.asdict(data), indent=2, ensure_ascii=False)


RENDERERS: dict[str, Any] = {"markdown": to_markdown, "text": to_text, "html": to_html, "json": to_json}
EXTENSIONS = {".md": "markdown", ".markdown": "markdown", ".txt": "text", ".html": "html", ".htm": "html",
             ".json": "json"}  # fmt: skip


def format_for(path: Path, fallback: str = "markdown") -> str:
    return EXTENSIONS.get(path.suffix.lower(), fallback)


def render(data: ReportData, fmt: str) -> str:
    return RENDERERS[fmt](data)  # type: ignore[no-any-return]


def write_report(data: ReportData, path: Path, fmt: str | None = None) -> None:
    path.write_text(render(data, fmt or format_for(path)), encoding="utf-8")
