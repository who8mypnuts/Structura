"""Line numbers and diagnostic markers beside the editor (docs/12 §2.1, §7)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent
from PySide6.QtWidgets import QWidget

from ...core.lang.diagnostics import Severity

if TYPE_CHECKING:
    from .code_editor import CodeEditor

MARKER = {Severity.ERROR: "●", Severity.WARNING: "▲", Severity.INFO: "■", Severity.HINT: "·"}  # shape-coded


class Gutter(QWidget):
    def __init__(self, editor: CodeEditor) -> None:
        super().__init__(editor)
        self.editor = editor
        self.colors = {"fg": QColor("#888"), "active": QColor("#ddd"), "bg": QColor("#222")}
        self.markers: dict[int, tuple[Severity, QColor]] = {}  # block number → worst diagnostic

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(self.width_needed(), 0)

    def width_needed(self) -> int:
        digits = max(3, len(str(max(1, self.editor.blockCount()))))
        return 22 + self.editor.fontMetrics().horizontalAdvance("9") * digits

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
                painter.drawText(QRect(0, top, self.width() - 8, height), Qt.AlignmentFlag.AlignRight, str(number + 1))
                if number in self.markers:
                    severity, color = self.markers[number]
                    painter.setPen(color)
                    painter.drawText(QRect(2, top, 14, height), Qt.AlignmentFlag.AlignCenter, MARKER[severity])
            block, top = block.next(), bottom
