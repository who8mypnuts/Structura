"""Problems panel: the diagnostics of the active document (docs/12 §7)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget

from ...core.lang.diagnostics import Diagnostic, Severity
from ...core.lang.source import LineIndex
from ..editor.gutter import MARKER

SPAN_ROLE = Qt.ItemDataRole.UserRole


class ProblemsPanel(QTreeWidget):
    activated_offset = Signal(int)  # jump to this text offset
    count_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setHeaderLabels(["", "Code", "Message", "Line"])
        self.setRootIsDecorated(False)
        self.setColumnWidth(0, 28)
        self.setColumnWidth(1, 60)
        self.setColumnWidth(2, 420)
        self.itemActivated.connect(self._jump)
        self.itemClicked.connect(self._jump)

    def show_diagnostics(self, text: str, diagnostics: list[Diagnostic]) -> None:
        self.clear()
        index = LineIndex.of(text)
        for d in sorted(diagnostics, key=lambda d: (-d.severity, d.span.start if d.span else 0)):
            line = str(index.position(d.span.start)[0]) if d.span else ""
            item = QTreeWidgetItem([MARKER.get(d.severity, "·"), d.code, d.message, line])
            item.setData(0, SPAN_ROLE, d.span.start if d.span else -1)
            item.setToolTip(2, d.message)
            self.addTopLevelItem(item)
        self.count_changed.emit(sum(1 for d in diagnostics if d.severity >= Severity.WARNING))

    def _jump(self, item: QTreeWidgetItem, _column: int = 0) -> None:
        offset = item.data(0, SPAN_ROLE)
        if isinstance(offset, int) and offset >= 0:
            self.activated_offset.emit(offset)
