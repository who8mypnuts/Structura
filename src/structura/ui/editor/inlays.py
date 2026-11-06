"""Inlay hints (docs/12 §2.2): the probability of each alternative of an ambiguous rule, after its header."""

from __future__ import annotations

from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QPlainTextEdit

from ...core.lang.analysis import Analysis
from ..theming import qcolor


def rule_hints(analysis: Analysis) -> dict[int, str]:
    """Text offset of each ambiguous rule definition → its hint."""
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}
    for rule in analysis.rules:
        totals[rule.name] = totals.get(rule.name, 0.0) + rule.weight
        counts[rule.name] = counts.get(rule.name, 0) + 1
    return {
        r.span.start: f"⟶ {100 * r.weight / (totals[r.name] or 1):.1f}%" for r in analysis.rules if counts[r.name] > 1
    }


def paint_inlays(editor: QPlainTextEdit, painter: QPainter, analysis: Analysis | None, color: str) -> None:
    if analysis is None:
        return
    hints = rule_hints(analysis)
    if not hints:
        return
    painter.setPen(qcolor(color))
    metrics, offset = editor.fontMetrics(), editor.contentOffset()
    document = editor.document()
    for position, text in hints.items():
        block = document.findBlock(position)
        if not block.isValid() or not block.isVisible():
            continue
        top = editor.blockBoundingGeometry(block).translated(offset).top()
        if top < -metrics.height() or top > editor.viewport().height():
            continue
        x = document.documentMargin() + metrics.horizontalAdvance(block.text() + "   ")
        painter.drawText(QPointF(x, top + metrics.ascent()), text)
