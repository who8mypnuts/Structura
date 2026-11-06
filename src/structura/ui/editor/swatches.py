"""Colour swatches under colour literals (docs/12 §2.3), painted in the editor viewport."""

from __future__ import annotations

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QPlainTextEdit

from ...core.color import parse_color
from ...core.lang.highlight import lex_line
from .decorations import visible_blocks
from .highlighter import lexer_state

BAR = 3  # pixels


def color_of(token: str) -> QColor | None:
    parsed = parse_color(token)
    if parsed is None:
        return None
    return QColor.fromRgbF(parsed.r / 65535, parsed.g / 65535, parsed.b / 65535)


def paint_swatches(editor: QPlainTextEdit, painter: QPainter) -> None:
    metrics = editor.fontMetrics()
    margin = editor.document().documentMargin()
    for block, geometry in visible_blocks(editor):
        text = block.text()
        tokens, _ = lex_line(text, lexer_state(block.previous().userState()))
        for start, length, role in tokens:
            color = color_of(text[start : start + length]) if role == "color" else None
            if color is None:
                continue
            x = geometry.left() + margin + metrics.horizontalAdvance(text[:start])
            width = metrics.horizontalAdvance(text[start : start + length])
            y = geometry.top() + metrics.height() - 1
            painter.fillRect(QRectF(x, y, width, BAR), color)
