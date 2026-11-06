"""The keymap editor (docs/14 §4): every command with its shortcut. Pick a preset, filter, double-click a row
to record a new shortcut, and see conflicts marked. Only differences from the preset are stored."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..commands.keymap import PRESET_TITLES, Keymap, normal, presets

COLUMNS = ("Command", "Category", "Shortcut", "Preset default")


class KeymapEditor(QDialog):
    def __init__(self, keymap: Keymap, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Keyboard shortcuts")
        self.resize(760, 560)
        self.keymap = keymap
        self.preset = keymap.preset
        self.own = keymap.overrides()
        self.presets = QComboBox()
        for name in presets():
            self.presets.addItem(PRESET_TITLES.get(name, name), name)
        self.presets.setCurrentIndex(list(presets()).index(self.preset))
        self.presets.currentIndexChanged.connect(self._preset_changed)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter commands or shortcuts")
        self.filter.textChanged.connect(self._refresh)
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._record)
        self.recorder = QKeySequenceEdit()
        self.recorder.editingFinished.connect(self._recorded)
        self.recorder.hide()
        self.conflicts = QLabel()
        self.conflicts.setObjectName("Muted")
        self._layout()
        self._refresh()

    def _layout(self) -> None:
        top = QHBoxLayout()
        top.addWidget(QLabel("Preset"))
        top.addWidget(self.presets)
        top.addWidget(self.filter, 1)
        reset = QPushButton("Reset to preset")
        reset.clicked.connect(self._reset_all)
        clear = QPushButton("Remove shortcut")
        clear.clicked.connect(self._clear_selected)
        actions = QHBoxLayout()
        actions.addWidget(self.recorder, 1)
        actions.addWidget(clear)
        actions.addWidget(reset)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.table, 1)
        layout.addLayout(actions)
        layout.addWidget(self.conflicts)
        layout.addWidget(buttons)

    # -- view --------------------------------------------------------------------------------------------------
    def bindings(self) -> dict[str, str]:
        return self.keymap.effective(self.preset, self.own)

    def _refresh(self) -> None:
        bindings, needle = self.bindings(), self.filter.text().lower()
        clashes = self.keymap.conflicts(bindings)
        commands = [c for c in self.keymap.registry.commands()
                    if needle in f"{c.title} {c.category} {bindings[c.id]}".lower()]  # fmt: skip
        self.table.setRowCount(len(commands))
        for row, command in enumerate(commands):
            shortcut = bindings[command.id]
            cells = (command.title.replace("…", ""), command.category, shortcut,
                     self.keymap.default(command.id, self.preset))  # fmt: skip
            for column, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, command.id)
                if column == 2 and shortcut in clashes:
                    item.setForeground(QColor("#E5534B"))
                    item.setToolTip("Also bound to: " + ", ".join(i for i in clashes[shortcut] if i != command.id))
                if column == 2 and command.id in self.own:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.table.setItem(row, column, item)
        self.table.resizeColumnsToContents()
        self.conflicts.setText(f"{len(clashes)} conflicting shortcut(s): " + ", ".join(clashes) if clashes
                               else "No conflicts.")  # fmt: skip

    def _selected_id(self) -> str | None:
        item = self.table.item(self.table.currentRow(), 0)
        value = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        return str(value) if value else None

    # -- editing ----------------------------------------------------------------------------------------------
    def _preset_changed(self) -> None:
        self.preset = str(self.presets.currentData())
        self._refresh()

    def _record(self, row: int, _column: int) -> None:
        self.table.selectRow(row)
        self.recorder.clear()
        self.recorder.show()
        self.recorder.setFocus()

    def _recorded(self) -> None:
        command_id = self._selected_id()
        if command_id is not None:
            self.set_binding(command_id, self.recorder.keySequence().toString())
        self.recorder.hide()

    def set_binding(self, command_id: str, shortcut: str) -> None:
        """Bind ``shortcut`` (stored only when it differs from the preset)."""
        if normal(shortcut) == self.keymap.default(command_id, self.preset):
            self.own.pop(command_id, None)
        else:
            self.own[command_id] = normal(shortcut)
        self._refresh()

    def _clear_selected(self) -> None:
        command_id = self._selected_id()
        if command_id is not None:
            self.set_binding(command_id, "")

    def _reset_all(self) -> None:
        self.own = {}
        self._refresh()

    def accept(self) -> None:
        self.keymap.save(self.preset, self.own)
        super().accept()
