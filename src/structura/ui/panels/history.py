"""History panel (docs/14 §5.3 "snapshot strip"): snapshots of the current script while exploring — the text,
seed, parameters and camera, with a thumbnail of the viewport — to compare and restore earlier states."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from ...core.scene.camera import Camera
from ..i18n import tr

THUMB = QSize(128, 80)


@dataclass(frozen=True)
class Snapshot:
    text: str
    seed: int
    params: dict[str, float]
    camera: Camera
    image: QImage = field(compare=False)
    taken: str = field(default_factory=lambda: time.strftime("%H:%M:%S"))

    @property
    def label(self) -> str:
        return f"{self.taken} · seed {self.seed}"


class HistoryPanel(QWidget):
    take_requested = Signal()
    restore_requested = Signal(object)  # Snapshot

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.strip = QListWidget()
        self.strip.setAccessibleName(tr("Snapshots"))
        self.strip.setViewMode(QListWidget.ViewMode.IconMode)
        self.strip.setFlow(QListWidget.Flow.LeftToRight)
        self.strip.setWrapping(False)
        self.strip.setIconSize(THUMB)
        self.strip.setMovement(QListWidget.Movement.Static)
        self.strip.itemDoubleClicked.connect(self._restore)
        self.strip.itemActivated.connect(self._restore)
        take, restore, delete = QPushButton(tr("Take Snapshot")), QPushButton(tr("Restore")), QPushButton(tr("Delete"))
        take.setToolTip(tr("Keep the script, seed, parameters and camera as they are now (Ctrl+Alt+H)"))
        take.clicked.connect(self.take_requested)
        restore.clicked.connect(lambda: self._restore(self.strip.currentItem()))
        delete.clicked.connect(self._delete)
        buttons = QVBoxLayout()
        for button in (take, restore, delete):
            buttons.addWidget(button)
        buttons.addStretch(1)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.strip, 1)
        layout.addLayout(buttons)
        self.snapshots: list[Snapshot] = []

    def show_snapshots(self, snapshots: list[Snapshot]) -> None:
        """The current tab's list (the panel shows it; the tab owns it)."""
        self.snapshots = snapshots
        self.strip.clear()
        for snapshot in snapshots:
            small = snapshot.image.scaled(THUMB, Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation)  # fmt: skip
            icon = QIcon(QPixmap.fromImage(small))
            item = QListWidgetItem(icon, snapshot.label)
            params = ", ".join(f"{k} = {v:g}" for k, v in snapshot.params.items())
            item.setToolTip(f"{snapshot.label}\n{params}" if params else snapshot.label)
            self.strip.addItem(item)

    def _restore(self, item: QListWidgetItem | None) -> None:
        if item is not None:
            self.restore_requested.emit(self.snapshots[self.strip.row(item)])

    def _delete(self) -> None:
        row = self.strip.currentRow()
        if 0 <= row < len(self.snapshots):
            del self.snapshots[row]
            self.show_snapshots(self.snapshots)
