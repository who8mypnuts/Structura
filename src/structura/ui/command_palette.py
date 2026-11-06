"""Command palette (Ctrl+Shift+P): fuzzy search over every registered command (docs/14 §4)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QFrame, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from .commands.registry import Command, CommandRegistry


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


class CommandPalette(QFrame):
    def __init__(self, registry: CommandRegistry, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("CommandPalette")
        self.registry = registry
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a command")
        self.list = QListWidget()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self.input)
        layout.addWidget(self.list)
        self.input.textChanged.connect(self.refresh)
        self.input.installEventFilter(self)
        self.list.itemActivated.connect(self._run)
        self.hide()

    def open(self) -> None:
        parent = self.parentWidget()
        host_width = parent.width() if parent is not None else 700
        width = min(620, host_width - 40)
        self.setGeometry((host_width - width) // 2, 60, width, 380)
        self.input.clear()
        self.refresh()
        self.show()
        self.raise_()
        self.input.setFocus()

    def refresh(self) -> None:
        query = self.input.text()
        scored: list[tuple[int, Command]] = []
        for command in self.registry.commands():
            label = f"{command.category}: {command.title}"
            score = fuzzy_score(query, label)
            if score is not None and self.registry.action(command.id).isEnabled():
                scored.append((score, command))
        self.list.clear()
        for _, command in sorted(scored, key=lambda sc: (-sc[0], sc[1].title)):
            shortcut = self.registry.action(command.id).shortcut().toString()
            item = QListWidgetItem(f"{command.category}: {command.title}" + (f"    {shortcut}" if shortcut else ""))
            item.setData(Qt.ItemDataRole.UserRole, command.id)
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)

    def _run(self, item: QListWidgetItem) -> None:
        self.hide()
        self.registry.trigger(str(item.data(Qt.ItemDataRole.UserRole)))

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
                self._run(self.list.currentItem())
                return True
        return False
