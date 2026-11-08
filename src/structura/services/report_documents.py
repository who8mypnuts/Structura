"""PDF and OpenDocument reports through Qt's document engine (docs/09 §8.1), and the one entry point that
writes a report in any supported format."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QGuiApplication, QPageLayout, QPageSize, QPdfWriter, QTextDocument, QTextDocumentWriter

from ..render.report.html_writer import to_html
from ..render.report.model import Report
from ..render.report.writers import QT_FORMATS, write_text_report

PAGE_MARGIN_MM = 15.0
DPI = 300


def ensure_gui_application() -> None:
    """Qt's document engine needs fonts, which need a QGuiApplication (the CLI has none: use 'offscreen')."""
    if QGuiApplication.instance() is None:
        QGuiApplication(["structura", "-platform", "offscreen"])


def _document(report: Report) -> QTextDocument:
    document = QTextDocument()
    document.setDocumentMargin(0)
    document.setHtml(to_html(report))
    return document


def write_pdf(report: Report, path: Path) -> None:
    writer = QPdfWriter(str(path))
    writer.setResolution(DPI)
    writer.setTitle(report.title)
    writer.setCreator("Structura")
    margins = QMarginsF(PAGE_MARGIN_MM, PAGE_MARGIN_MM, PAGE_MARGIN_MM, PAGE_MARGIN_MM)
    writer.setPageLayout(QPageLayout(QPageSize(QPageSize.PageSizeId.A4), QPageLayout.Orientation.Portrait, margins,
                                     QPageLayout.Unit.Millimeter))  # fmt: skip
    _document(report).print_(writer)


def write_odt(report: Report, path: Path) -> None:
    writer = QTextDocumentWriter(str(path), b"odf")
    if not writer.write(_document(report)):
        raise OSError(f"could not write {path}")


def write_report(report: Report, path: Path) -> list[Path]:
    """Write ``report`` in the format named by ``path``'s suffix; returns every file written."""
    suffix = path.suffix.lower()
    if suffix not in QT_FORMATS:
        return write_text_report(report, path)
    ensure_gui_application()
    (write_pdf if suffix == ".pdf" else write_odt)(report, path)
    return [path]
