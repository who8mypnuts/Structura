"""Render Queue panel (docs/14 §3): queued, running and finished renders with progress, time and output."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr
from ..render_queue import QueueEntry, RenderQueue
from ..widgets.toast import reveal


class RenderQueuePanel(QWidget):
    add_requested = Signal()

    def __init__(self, queue: RenderQueue, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.queue = queue
        self.tree = QTreeWidget()
        self.tree.setAccessibleName(tr("Queued renders"))
        self.tree.setRootIsDecorated(False)
        self.tree.setHeaderLabels([tr("Render"), tr("State"), tr("Progress"), tr("Time"), tr("Output")])
        self.tree.setColumnWidth(0, 200)
        self.reports = QCheckBox(tr("Write a PDF report with each render"))
        buttons = QHBoxLayout()
        for text, slot in ((tr("Add Current View…"), self.add_requested.emit), (tr("Cancel"), self._cancel),
                           (tr("Remove"), self._remove), (tr("Show in Folder"), self._reveal),
                           (tr("Clear Finished"), queue.clear_finished)):  # fmt: skip
            button = QPushButton(text)
            button.clicked.connect(slot)
            buttons.addWidget(button)
        buttons.addStretch(1)
        buttons.addWidget(self.reports)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.tree, 1)
        layout.addLayout(buttons)
        queue.changed.connect(self.refresh)

    @Slot(object)
    def refresh(self, _entry: object = None) -> None:
        states = {"queued": tr("queued"), "rendering": tr("rendering"), "saving": tr("saving"), "done": tr("done"),
                  "failed": tr("failed"), "cancelled": tr("cancelled")}  # fmt: skip
        selected = self.selected()
        self.tree.clear()
        for entry in self.queue.entries:
            item = QTreeWidgetItem([entry.name, states.get(entry.state, entry.state), f"{entry.fraction:.0%}",
                                    f"{entry.seconds:.1f} s", str(entry.path)])  # fmt: skip
            item.setToolTip(1, entry.message)
            item.setData(0, Qt.ItemDataRole.UserRole, entry.doc_id)
            self.tree.addTopLevelItem(item)
            item.setSelected(entry is selected)

    def selected(self) -> QueueEntry | None:
        items = self.tree.selectedItems()
        return self.queue.entry(str(items[0].data(0, Qt.ItemDataRole.UserRole))) if items else None

    def _cancel(self) -> None:
        entry = self.selected()
        if entry is not None:
            self.queue.cancel(entry)

    def _remove(self) -> None:
        entry = self.selected()
        if entry is not None:
            self.queue.remove(entry)

    def _reveal(self) -> None:
        entry = self.selected()
        if entry is not None:
            reveal(entry.path)()
