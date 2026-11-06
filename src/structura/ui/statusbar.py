"""Status bar segments (docs/14 §6): cursor, dialect, object count, build time, device, activity."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QProgressBar, QStatusBar, QWidget


class StatusBar(QStatusBar):
    SEGMENTS = ("cursor", "dialect", "objects", "build", "device")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.labels = {name: QLabel("") for name in self.SEGMENTS}
        self.labels["cursor"].setMinimumWidth(110)  # permanent widgets keep their first size hint otherwise
        self.busy = QProgressBar()
        self.busy.setRange(0, 0)  # indeterminate spinner while a build runs
        self.busy.setMaximumWidth(90)
        self.busy.hide()
        for name in self.SEGMENTS:
            self.addPermanentWidget(self.labels[name])
        self.addPermanentWidget(self.busy)
        self.set("dialect", "EisenScript v1")

    def set(self, segment: str, text: str) -> None:
        self.labels[segment].setText(text)

    def set_busy(self, busy: bool) -> None:
        self.busy.setVisible(busy)
