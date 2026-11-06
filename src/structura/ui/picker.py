"""PickerPopup: a filter box over a ranked list, shown at the top of the window (docs/14 §4). The command
palette and Quick Open are pickers; subclasses supply the entries and what choosing one does."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QFrame, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from .i18n import tr

Entry = tuple[str, str, Any]  # (label, detail shown on the right, payload)


def fuzzy_score(query: str, text: str) -> int | None:
    """Higher is better; None when the query's characters do not appear in order."""
    q, t = query.lower(), text.lower()
    if not q:
        return 0
    if q in t:
        return 1000 - t.index(q)
    pos, score = 0, 0
    for ch in q:
        found = t.find(ch, pos)
        if found < 0:
            return None
        score += 10 - min(9, found - pos)
        pos = found + 1
    return score


def ranked(query: str, entries: list[Entry]) -> list[Entry]:
    """Entries matching ``query``, best first (ties keep their order)."""
    scored = [(score, i, e) for i, e in enumerate(entries) if (score := fuzzy_score(query, e[0])) is not None]
    return [e for _, _, e in sorted(scored, key=lambda s: (-s[0], s[1]))]


class PickerPopup(QFrame):
    placeholder = "Type to filter"

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("CommandPalette")
        self.input = QLineEdit()
        self.input.setAccessibleName(tr("Filter"))
        self.input.setPlaceholderText(self.placeholder)
        self.list = QListWidget()
        self.list.setAccessibleName(tr("Matches"))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self.input)
        layout.addWidget(self.list)
        self.input.textChanged.connect(self.refresh)
        self.input.installEventFilter(self)
        self.list.itemActivated.connect(self._choose)
        self.hide()

    # -- for subclasses ------------------------------------------------------------------------------------
    def entries(self, query: str) -> list[Entry]:
        raise NotImplementedError

    def activate(self, payload: Any) -> None:
        raise NotImplementedError

    # -- behaviour --------------------------------------------------------------------------------------------
    def open(self, text: str = "") -> None:
        parent = self.parentWidget()
        host_width = parent.width() if parent is not None else 700
        width = min(620, host_width - 40)
        self.setGeometry((host_width - width) // 2, 60, width, 380)
        self.input.setText(text)
        self.refresh()
        self.show()
        self.raise_()
        self.input.setFocus()

    def refresh(self) -> None:
        self.list.clear()
        for label, detail, payload in self.entries(self.input.text()):
            item = QListWidgetItem(label + (f"    {detail}" if detail else ""))
            item.setData(Qt.ItemDataRole.UserRole, payload)
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)

    def _choose(self, item: QListWidgetItem) -> None:
        self.hide()
        self.activate(item.data(Qt.ItemDataRole.UserRole))

    def eventFilter(self, watched: object, event: object) -> bool:  # noqa: N802
        if isinstance(event, QKeyEvent) and event.type() == QKeyEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Escape:
                self.hide()
                return True
            if key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                row = self.list.currentRow() + (1 if key == Qt.Key.Key_Down else -1)
                self.list.setCurrentRow(max(0, min(self.list.count() - 1, row)))
                return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.list.currentItem():
                self._choose(self.list.currentItem())
                return True
        return False
