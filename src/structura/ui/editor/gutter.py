"""Line numbers, diagnostic markers and fold markers beside the editor (docs/12 §2.1, §7)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QTextBlock
from PySide6.QtWidgets import QWidget

from ...core.lang.diagnostics import Severity

if TYPE_CHECKING:
    from .code_editor import CodeEditor

MARKER = {Severity.ERROR: "●", Severity.WARNING: "▲", Severity.INFO: "■", Severity.HINT: "·"}  # shape-coded
FOLD_WIDTH = 14
FOLDED, OPEN = "▸", "▾"


class Gutter(QWidget):
    def __init__(self, editor: CodeEditor) -> None:
        super().__init__(editor)
        self.editor = editor
        self.colors = {"fg": QColor("#888"), "active": QColor("#ddd"), "bg": QColor("#222"), "fold": QColor("#888")}
        self.markers: dict[int, tuple[Severity, QColor]] = {}  # block number → worst diagnostic

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(self.width_needed(), 0)

    def width_needed(self) -> int:
        digits = max(3, len(str(max(1, self.editor.blockCount()))))
        return 22 + FOLD_WIDTH + self.editor.fontMetrics().horizontalAdvance("9") * digits

    def block_at(self, y: float) -> QTextBlock | None:
        editor = self.editor
        block = editor.firstVisibleBlock()
        top = editor.blockBoundingGeometry(block).translated(editor.contentOffset()).top()
        while block.isValid():
            if block.isVisible():
                bottom = top + editor.blockBoundingRect(block).height()
                if top <= y < bottom:
                    return block
                top = bottom
            block = block.next()
        return None

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        block = self.block_at(event.position().y())
        if block is not None and event.position().x() >= self.width() - FOLD_WIDTH:
            self.editor.folding.toggle(block.blockNumber())
            return
        super().mousePressEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(event.rect(), self.colors["bg"])
        editor = self.editor
        block = editor.firstVisibleBlock()
        current = editor.textCursor().blockNumber()
        top = round(editor.blockBoundingGeometry(block).translated(editor.contentOffset()).top())
        height = editor.fontMetrics().height()
        while block.isValid() and top <= event.rect().bottom():
            bottom = top + round(editor.blockBoundingRect(block).height())
            if block.isVisible() and bottom >= event.rect().top():
                number = block.blockNumber()
                painter.setPen(self.colors["active" if number == current else "fg"])
                number_rect = QRect(0, top, self.width() - FOLD_WIDTH - 4, height)
                painter.drawText(number_rect, Qt.AlignmentFlag.AlignRight, str(number + 1))
                self._paint_fold(painter, number, top, height)
                if number in self.markers:
                    severity, color = self.markers[number]
                    painter.setPen(color)
                    painter.drawText(QRect(2, top, 14, height), Qt.AlignmentFlag.AlignCenter, MARKER[severity])
            block, top = block.next(), bottom
        self._paint_sticky_numbers(painter, height)

    def _paint_sticky_numbers(self, painter: QPainter, height: int) -> None:
        """Beside pinned sticky headers, show the headers' own line numbers."""
        sticky = self.editor.sticky
        if not sticky.isVisible():
            return
        for row, number in enumerate(sticky.headers):
            rect = QRect(0, row * height, self.width(), height)
            painter.fillRect(rect, self.colors["bg"])
            painter.setPen(self.colors["fg"])
            painter.drawText(rect.adjusted(0, 0, -FOLD_WIDTH - 4, 0), Qt.AlignmentFlag.AlignRight, str(number + 1))

    def _paint_fold(self, painter: QPainter, number: int, top: int, height: int) -> None:
        folding = self.editor.folding
        if number not in folding.ranges:
            return
        painter.setPen(self.colors["fold"])
        glyph = FOLDED if folding.is_folded(number) else OPEN
        painter.drawText(QRect(self.width() - FOLD_WIDTH, top, FOLD_WIDTH, height), Qt.AlignmentFlag.AlignCenter, glyph)
