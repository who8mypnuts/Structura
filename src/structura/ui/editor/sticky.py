"""Sticky scroll (docs/12 §2.1): while the body of a rule is scrolled past its header, the header lines of
the enclosing rules/blocks stay pinned at the top of the editor (up to MAX_LEVELS). Click one to jump to it.
Headers come from the fold ranges, so nesting follows braces exactly."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import QWidget

from ...core.lang.highlight import lex_line
from ...themes.model import Theme
from ..theming import qcolor, syntax_format
from .highlighter import lexer_state

if TYPE_CHECKING:
    from .code_editor import CodeEditor

MAX_LEVELS = 3


def _segments(
    text: str, tokens: list[tuple[int, int, str]], default: QColor, theme: Theme
) -> list[tuple[int, int, QColor]]:
    """The whole line as (start, end, colour) spans: tokens in their syntax colour, gaps in the default."""
    out, position = [], 0
    for start, length, role in tokens:
        if start > position:
            out.append((position, start, default))
        out.append((start, start + length, syntax_format(theme, role).foreground().color()))
        position = start + length
    if position < len(text):
        out.append((position, len(text), default))
    return out


class StickyHeaders(QWidget):
    def __init__(self, editor: CodeEditor) -> None:
        super().__init__(editor.viewport())
        self.editor = editor
        self.headers: list[int] = []  # block numbers of the pinned header lines, outermost first
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        editor.verticalScrollBar().valueChanged.connect(self.refresh)
        editor.document().contentsChanged.connect(self.refresh)
        self.hide()

    def refresh(self) -> None:
        if not self.editor.options.sticky_scroll:
            self.hide()
            return
        first = self.editor.firstVisibleBlock().blockNumber()
        enclosing = sorted((r for r in self.editor.folding.ranges.values()
                            if r.kind == "block" and r.start < first <= r.end), key=lambda r: r.start)  # fmt: skip
        self.headers = [r.start for r in enclosing][-MAX_LEVELS:]
        if not self.headers:
            self.hide()
            self.editor.gutter.update()
            return
        line = self.editor.fontMetrics().height()
        self.setGeometry(0, 0, self.editor.viewport().width(), line * len(self.headers) + 1)
        self.show()
        self.raise_()
        self.update()
        self.editor.gutter.update()  # it shows the headers' line numbers

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setFont(self.editor.font())  # the widget's own font is the UI font (application style sheet)
        theme = self.editor.theme
        painter.fillRect(self.rect(), qcolor(theme["editor.sticky.bg"]))
        metrics, margin = self.editor.fontMetrics(), self.editor.document().documentMargin()
        offset_x = self.editor.contentOffset().x()
        for row, number in enumerate(self.headers):
            block = self.editor.document().findBlockByNumber(number)
            text = block.text()
            tokens, _ = lex_line(text, lexer_state(block.previous().userState()) if block.previous().isValid() else 0)
            baseline = row * metrics.height() + metrics.ascent()
            for start, end, colour in _segments(text, tokens, qcolor(theme["editor.fg"]), theme):
                painter.setPen(colour)
                x = margin + offset_x + metrics.horizontalAdvance(text[:start])
                painter.drawText(QPointF(x, baseline), text[start:end])
        painter.setPen(qcolor(theme["ui.border"]))
        painter.drawLine(QRectF(self.rect()).bottomLeft(), QRectF(self.rect()).bottomRight())

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        row = int(event.position().y() // max(1, self.editor.fontMetrics().height()))
        if 0 <= row < len(self.headers):
            self.editor.go_to(self.editor.document().findBlockByNumber(self.headers[row]).position())
