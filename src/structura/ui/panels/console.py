"""Console panel: application log records, delivered thread-safely through a Qt signal (docs/02 §6.6)."""

from __future__ import annotations

import contextlib
import logging
import time

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QPlainTextEdit, QWidget

MAX_BLOCKS = 5000


class LogBridge(QObject, logging.Handler):
    """A logging.Handler that re-emits records as a signal (queued to the GUI thread)."""

    record = Signal(str, int)

    def __init__(self) -> None:
        QObject.__init__(self)
        logging.Handler.__init__(self, logging.INFO)

    def emit(self, record: logging.LogRecord) -> None:  # type: ignore[override]
        with contextlib.suppress(RuntimeError):  # the bridge was deleted during shutdown
            self.record.emit(self.format(record), record.levelno)


class ConsolePanel(QPlainTextEdit):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(MAX_BLOCKS)
        self.bridge = LogBridge()
        self.bridge.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        self.bridge.record.connect(self.append_record)

    def attach(self, logger: logging.Logger | None = None) -> None:
        (logger or logging.getLogger("structura")).addHandler(self.bridge)

    def detach(self, logger: logging.Logger | None = None) -> None:
        (logger or logging.getLogger("structura")).removeHandler(self.bridge)

    @Slot(str, int)
    def append_record(self, text: str, level: int) -> None:
        self.appendPlainText(f"{time.strftime('%H:%M:%S')}  {text}")

    def info(self, text: str) -> None:
        self.append_record(text, logging.INFO)
