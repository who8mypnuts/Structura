"""Activity panel (docs/14 §3): every background job with its lane, state, progress and duration — builds,
renders, exports, warm-up. A debugging aid; running jobs can be cancelled from here."""

from __future__ import annotations

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from ...services.jobs import JobRunner
from ...services.jobs.runner import JobHandle
from ..i18n import tr

KEEP = 300  # finished jobs kept in the list


class ActivityPanel(QWidget):
    def __init__(self, runner: JobRunner, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.tree = QTreeWidget()
        self.tree.setAccessibleName(tr("Background jobs"))
        self.tree.setRootIsDecorated(False)
        self.tree.setHeaderLabels([tr("Job"), tr("Lane"), tr("State"), tr("Time"), tr("Progress")])
        self.tree.setColumnWidth(0, 220)
        cancel, clear = QPushButton(tr("Cancel Job")), QPushButton(tr("Clear Finished"))
        cancel.clicked.connect(self.cancel_selected)
        clear.clicked.connect(self.clear_finished)
        buttons = QHBoxLayout()
        buttons.addWidget(cancel)
        buttons.addWidget(clear)
        buttons.addStretch(1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.tree, 1)
        layout.addLayout(buttons)
        self.items: dict[JobHandle, QTreeWidgetItem] = {}
        runner.job_submitted.connect(self.add)

    @Slot(object)
    def add(self, handle: JobHandle) -> None:
        item = QTreeWidgetItem([handle.job.name, handle.job.lane.value, tr("queued"), "", ""])
        self.tree.insertTopLevelItem(0, item)
        self.items[handle] = item
        handle.started.connect(self._started)
        handle.progress.connect(self._progress)
        handle.ended.connect(self._ended)
        while self.tree.topLevelItemCount() > KEEP:
            self._drop(self.tree.topLevelItemCount() - 1)

    def _drop(self, index: int) -> None:
        item = self.tree.takeTopLevelItem(index)
        for handle, shown in list(self.items.items()):
            if shown is item:
                del self.items[handle]

    def _item(self) -> tuple[JobHandle, QTreeWidgetItem] | None:
        handle = self.sender()
        item = self.items.get(handle) if isinstance(handle, JobHandle) else None
        return (handle, item) if item is not None and isinstance(handle, JobHandle) else None

    @Slot()
    def _started(self) -> None:
        found = self._item()
        if found is not None:
            found[1].setText(2, tr("running"))

    @Slot(float, str)
    def _progress(self, fraction: float, text: str) -> None:
        found = self._item()
        if found is not None:
            found[1].setText(4, text or f"{fraction:.0%}")

    @Slot()
    def _ended(self) -> None:
        found = self._item()
        if found is None:
            return
        handle, item = found
        states = {"finished": tr("finished"), "failed": tr("failed"), "cancelled": tr("cancelled")}
        item.setText(2, states.get(handle.state, handle.state))
        item.setText(3, f"{handle.seconds:.2f} s")

    def cancel_selected(self) -> None:
        for handle, item in self.items.items():
            if item.isSelected() and not handle.done:
                handle.cancel()

    def clear_finished(self) -> None:
        for index in reversed(range(self.tree.topLevelItemCount())):
            item = self.tree.topLevelItem(index)
            handle = next((h for h, shown in self.items.items() if shown is item), None)
            if handle is None or handle.done:
                self._drop(index)

    def running(self) -> list[str]:
        return [h.job.name for h, item in self.items.items() if item.text(2) == tr("running")]
