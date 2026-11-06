"""Viewport decorations painted over the editor text (docs/12 §2.1): indentation guides and the '⋯'
placeholder after folded headers. All painters share ``visible_blocks``."""

from __future__ import annotations

from collections.abc import Iterator

from PySide6.QtCore import QLineF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QTextBlock
from PySide6.QtWidgets import QPlainTextEdit

from . import editing

FOLD_PLACEHOLDER = " ⋯ "


def visible_blocks(editor: QPlainTextEdit) -> Iterator[tuple[QTextBlock, QRectF]]:
    """Visible (unfolded) blocks intersecting the viewport, with their geometry in viewport coordinates."""
    block = editor.firstVisibleBlock()
    offset = editor.contentOffset()
    height = editor.viewport().height()
    while block.isValid():
        geometry = editor.blockBoundingGeometry(block).translated(offset)
        if geometry.top() > height:
            return
        if block.isVisible():
            yield block, geometry
        block = block.next()


def indent_width(text: str) -> int:
    """Leading indentation in columns (a tab counts as one indent step)."""
    lead = editing.leading_indent(text)
    return lead.count("\t") * len(editing.INDENT) + lead.count(" ")


def _guide_columns(block: QTextBlock) -> int:
    """Indent columns for a block; a blank line takes the indentation of the next non-blank line."""
    probe = block
    while probe.isValid() and not probe.text().strip():
        probe = probe.next()
    return indent_width(probe.text()) if probe.isValid() else 0


def paint_indent_guides(editor: QPlainTextEdit, painter: QPainter, color: QColor) -> None:
    painter.setPen(QPen(color, 1))
    step = len(editing.INDENT)
    space = editor.fontMetrics().horizontalAdvance(" ")
    left = editor.document().documentMargin()
    for block, geometry in visible_blocks(editor):
        for column in range(step, _guide_columns(block), step):  # no guide at column 0
            x = round(geometry.left() + left + column * space) + 0.5
            painter.drawLine(QLineF(x, geometry.top(), x, geometry.bottom()))


def paint_fold_placeholders(
    editor: QPlainTextEdit, painter: QPainter, folded: set[int], fg: QColor, bg: QColor
) -> None:
    if not folded:
        return
    metrics = editor.fontMetrics()
    left = editor.document().documentMargin()
    for block, geometry in visible_blocks(editor):
        if block.blockNumber() not in folded:
            continue
        x = geometry.left() + left + metrics.horizontalAdvance(block.text() + " ")
        box = QRectF(x, geometry.top() + 1, metrics.horizontalAdvance(FOLD_PLACEHOLDER), metrics.height() - 2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(box, 3, 3)
        painter.setPen(fg)
        painter.drawText(box, Qt.AlignmentFlag.AlignCenter, FOLD_PLACEHOLDER.strip())
