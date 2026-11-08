"""PDF rendering of the render report (docs/09 §11). This is the one format that needs Qt — so it lives
here, not in ``render.report``, which stays Qt-free. ``QTextDocument`` understands the report's HTML well
enough (plain tables, no flexbox or grid; ``report.html.j2`` avoids both for this reason).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QPageSize, QTextDocument
from PySide6.QtPrintSupport import QPrinter

from ..render.report import ReportData, to_html


def write_pdf(data: ReportData, path: Path) -> None:
    document = QTextDocument()
    document.setHtml(to_html(data))
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    printer.setOutputFileName(str(path))
    document.print_(printer)
