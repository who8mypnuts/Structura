"""Outline panel: rule definitions of the active document; click to jump (docs/14 §3)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget

from ...core.lang.analysis import Analysis


class OutlinePanel(QTreeWidget):
    activated_offset = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setHeaderLabels(["Rule", "Weight", "Uses"])
        self.setRootIsDecorated(False)
        self.itemClicked.connect(
            lambda item, _c: self.activated_offset.emit(int(item.data(0, Qt.ItemDataRole.UserRole)))
        )

    def show_analysis(self, analysis: Analysis) -> None:
        self.clear()
        for rule in analysis.rules:
            uses = len(analysis.references.get(rule.name, ()))
            item = QTreeWidgetItem([rule.name, f"{rule.weight:g}", str(uses)])
            item.setData(0, Qt.ItemDataRole.UserRole, rule.span.start)
            self.addTopLevelItem(item)
