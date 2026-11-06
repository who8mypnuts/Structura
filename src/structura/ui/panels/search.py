"""Find in Files panel (docs/12 §2.1): search the open documents and the scripts in the current file's
folder. Results are grouped by file; activate one to open it at the match."""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.text_search import Match, pattern, search
from ..i18n import tr

DEBOUNCE_MS = 250


class SearchPanel(QWidget):
    open_match = Signal(str, int)  # source (a file path or 'tab:<doc id>'), offset
    texts_wanted = Signal()  # asks the window for the texts to search (it calls search_in)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(DEBOUNCE_MS)
        self._timer.timeout.connect(self.texts_wanted)
        self.query = QLineEdit()
        self.query.setAccessibleName(tr("Find in files"))
        self.query.setPlaceholderText(tr("Find in open scripts and the current folder"))
        self.options = {name: QCheckBox(name) for name in ("Aa", "Word", ".*")}
        for box in self.options.values():
            box.toggled.connect(lambda _on: self._timer.start())
        self.summary = QLabel("")
        self.summary.setObjectName("Muted")
        self.tree = QTreeWidget()
        self.tree.setAccessibleName(tr("Search results"))
        self.tree.setHeaderHidden(True)
        self.tree.itemActivated.connect(self._activated)
        self.query.textChanged.connect(lambda _t: self._timer.start())
        row = QHBoxLayout()
        row.addWidget(self.query, 1)
        for box in self.options.values():
            row.addWidget(box)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addLayout(row)
        layout.addWidget(self.summary)
        layout.addWidget(self.tree, 1)

    def search_in(self, texts: dict[str, str], labels: dict[str, str]) -> list[Match]:
        """Run the current query over ``texts`` (source → text); ``labels`` names each source."""
        self.tree.clear()
        if not self.query.text():
            self.summary.setText("")
            return []
        try:
            compiled = pattern(self.query.text(), self.options[".*"].isChecked(), self.options["Aa"].isChecked(),
                               self.options["Word"].isChecked())  # fmt: skip
        except re.error as exc:
            self.summary.setText(f"Invalid regular expression: {exc}")
            return []
        matches = search(texts, compiled)
        groups: dict[str, QTreeWidgetItem] = {}
        for m in matches:
            if m.source not in groups:
                groups[m.source] = QTreeWidgetItem(self.tree, [labels.get(m.source, Path(m.source).name)])
                groups[m.source].setExpanded(True)
            item = QTreeWidgetItem(groups[m.source], [f"{m.line + 1}: {m.text.strip()}"])
            item.setData(0, Qt.ItemDataRole.UserRole, (m.source, m.offset))
        files = len(groups)
        self.summary.setText(f"{len(matches)} result{'s' if len(matches) != 1 else ''} in {files} file"
                             f"{'s' if files != 1 else ''}")  # fmt: skip
        return matches

    def _activated(self, item: QTreeWidgetItem) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data:
            self.open_match.emit(str(data[0]), int(data[1]))

    def focus_query(self) -> None:
        self.query.setFocus()
        self.query.selectAll()
