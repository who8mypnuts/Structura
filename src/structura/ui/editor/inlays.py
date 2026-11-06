"""Inlay hints (docs/12 §2.2): the analysis's hints (core.lang.inlay), drawn after the text of their line."""

from __future__ import annotations

from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QPlainTextEdit

from ...core.lang.analysis import Analysis
from ..theming import qcolor

GAP = "   "


def hints_by_line(editor: QPlainTextEdit, analysis: Analysis) -> dict[int, str]:
    """Block number → the hints of that line, joined."""
    document, lines = editor.document(), dict[int, str]()
    for hint in analysis.hints:
        number = document.findBlock(hint.position).blockNumber()
        lines[number] = f"{lines[number]}  {hint.text}" if number in lines else hint.text
    return lines


def paint_inlays(editor: QPlainTextEdit, painter: QPainter, analysis: Analysis | None, color: str) -> None:
    if analysis is None or not analysis.hints:
        return
    painter.setPen(qcolor(color))
    metrics, offset = editor.fontMetrics(), editor.contentOffset()
    document = editor.document()
    for number, text in hints_by_line(editor, analysis).items():
        block = document.findBlockByNumber(number)
        if not block.isValid() or not block.isVisible():
            continue
        top = editor.blockBoundingGeometry(block).translated(offset).top()
        if top < -metrics.height() or top > editor.viewport().height():
            continue
        x = offset.x() + document.documentMargin() + metrics.horizontalAdvance(block.text() + GAP)
        painter.drawText(QPointF(x, top + metrics.ascent()), text)
