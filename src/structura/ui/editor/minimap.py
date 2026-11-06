"""The minimap (docs/12 §2.1): a narrow overview at the editor's right edge. Tokens are drawn as coloured
bars (one pixel per character, LINE_HEIGHT per line), diagnostics as ticks on the right, and the visible
range as a translucent band. Click or drag scrolls. The picture is cached and rebuilt after edits."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import QWidget

from ...core.lang.highlight import lex_line
from ..theming import qcolor, syntax_format
from .highlighter import lexer_state

if TYPE_CHECKING:
    from .code_editor import CodeEditor

WIDTH, LINE_HEIGHT, COLUMNS = 84, 2, 80
REBUILD_MS = 150


class Minimap(QWidget):
    def __init__(self, editor: CodeEditor) -> None:
        super().__init__(editor)
        self.editor = editor
        self.image = QImage()
        self.lines: list[int] = []  # block number of each drawn (visible) line
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(REBUILD_MS)
        self._timer.timeout.connect(self.rebuild)
        editor.document().contentsChanged.connect(self._timer.start)
        editor.verticalScrollBar().valueChanged.connect(self.update)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    # -- picture -----------------------------------------------------------------------------------------
    def _colours(self) -> dict[str, QColor]:
        theme = self.editor.theme
        roles = ("keyword", "operator", "modifier", "number", "color", "primitive", "rule.def", "rule.ref",
                 "tag", "brace", "comment", "preprocessor", "set.key", "set.value", "string", "block")  # fmt: skip
        return {role: syntax_format(theme, role).foreground().color() for role in roles}

    def rebuild(self) -> None:
        blocks = []
        block = self.editor.document().begin()
        while block.isValid():
            if block.isVisible():
                blocks.append(block)
            block = block.next()
        self.lines = [b.blockNumber() for b in blocks]
        image = QImage(COLUMNS, max(1, len(blocks) * LINE_HEIGHT), QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        colours, fallback = self._colours(), qcolor(self.editor.theme["editor.fg"])
        for row, b in enumerate(blocks):
            text = b.text()
            tokens, _ = lex_line(text, lexer_state(b.previous().userState()) if b.previous().isValid() else 0)
            for start, length, role in tokens:
                if start >= COLUMNS or not text[start : start + length].strip():
                    continue
                colour = QColor(colours.get(role, fallback))
                colour.setAlphaF(0.85)
                painter.fillRect(QRectF(start, row * LINE_HEIGHT, min(length, COLUMNS - start), LINE_HEIGHT - 0.5),
                                 colour)  # fmt: skip
        painter.end()
        self.image = image
        self.update()

    # -- geometry --------------------------------------------------------------------------------------------
    def _offset(self) -> float:
        """How far the minimap itself is scrolled (long scripts do not fit)."""
        bar = self.editor.verticalScrollBar()
        overflow = max(0, len(self.lines) * LINE_HEIGHT - self.height())
        return overflow * (bar.value() / bar.maximum()) if bar.maximum() else 0.0

    def _row_of(self, block_number: int) -> int:
        for row, number in enumerate(self.lines):
            if number >= block_number:
                return row
        return len(self.lines)

    def _visible_band(self) -> QRectF:
        first = self.editor.firstVisibleBlock().blockNumber()
        rows = max(1, self.editor.viewport().height() // max(1, self.editor.fontMetrics().height()))
        top = self._row_of(first) * LINE_HEIGHT - self._offset()
        return QRectF(0, top, self.width(), rows * LINE_HEIGHT)

    # -- painting and scrolling ------------------------------------------------------------------------------
    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), qcolor(self.editor.theme["editor.bg"]))
        if not self.image.isNull():
            painter.drawImage(QRectF(2, -self._offset(), COLUMNS, self.image.height()), self.image)
        band = QColor(qcolor(self.editor.theme["editor.fg"]))
        band.setAlphaF(0.10)
        painter.fillRect(self._visible_band(), band)
        for number, (_severity, colour) in self.editor.gutter.markers.items():
            y = self._row_of(number) * LINE_HEIGHT - self._offset()
            painter.fillRect(QRectF(self.width() - 4, y - 1, 4, 3), colour)

    def _scroll_to(self, y: float) -> None:
        row = int((y + self._offset()) / LINE_HEIGHT)
        if not self.lines:
            return
        block = self.editor.document().findBlockByNumber(self.lines[max(0, min(row, len(self.lines) - 1))])
        rows = max(1, self.editor.viewport().height() // max(1, self.editor.fontMetrics().height()))
        target = max(0, block.firstLineNumber() - rows // 2)
        self.editor.verticalScrollBar().setValue(target)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._scroll_to(event.position().y())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._scroll_to(event.position().y())
