"""Drag & drop files onto the main window to open them (docs/12 §2.1). The code editor refuses file drops
(see CodeEditor.canInsertFromMimeData), so they propagate here instead of pasting the path as text."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QEvent, QMimeData, QObject
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QWidget


def local_files(mime: QMimeData | None) -> list[Path]:
    if mime is None or not mime.hasUrls():
        return []
    return [Path(url.toLocalFile()) for url in mime.urls() if url.isLocalFile() and Path(url.toLocalFile()).is_file()]


class FileDropFilter(QObject):
    def __init__(self, target: QWidget, open_file: Callable[[Path], object]) -> None:
        super().__init__(target)
        self.open_file = open_file
        target.setAcceptDrops(True)
        target.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if isinstance(event, QDragEnterEvent | QDropEvent) and local_files(event.mimeData()):
            event.acceptProposedAction()
            if event.type() == QEvent.Type.Drop:
                for path in local_files(event.mimeData()):
                    self.open_file(path)
            return True
        return False
