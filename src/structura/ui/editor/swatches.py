"""Colour swatches under colour literals (docs/12 §2.3), painted in the editor viewport."""

from __future__ import annotations

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QPlainTextEdit

from ...core.color import parse_color
from ...core.lang.highlight import lex_line

BAR = 3  # pixels


def color_of(token: str) -> QColor | None:
    parsed = parse_color(token)
    if parsed is None:
        return None
    return QColor.fromRgbF(parsed.r / 65535, parsed.g / 65535, parsed.b / 65535)


def paint_swatches(editor: QPlainTextEdit, painter: QPainter) -> None:
    block = editor.firstVisibleBlock()
    offset = editor.contentOffset()
    metrics = editor.fontMetrics()
    state = max(block.previous().userState(), 0) if block.previous().isValid() else 0
    while block.isValid():
        geometry = editor.blockBoundingGeometry(block).translated(offset)
        if geometry.top() > editor.viewport().height():
            break
        text = block.text()
        tokens, state = lex_line(text, state)
        for start, length, role in tokens:
            color = color_of(text[start : start + length]) if role == "color" else None
            if color is None:
                continue
            x = geometry.left() + editor.document().documentMargin() + metrics.horizontalAdvance(text[:start])
            width = metrics.horizontalAdvance(text[start : start + length])
            y = geometry.top() + metrics.height() - 1
            painter.fillRect(QRectF(x, y, width, BAR), color)
        block = block.next()
