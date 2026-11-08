"""Console panel (docs/14 §3): application log records, delivered thread-safely through a Qt signal (docs/02
§6.6), with a severity filter, a search box, Copy and Clear."""

from __future__ import annotations

import contextlib
import html
import logging
import time
from collections import deque

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from ..i18n import tr

MAX_RECORDS = 5000
LEVELS = (("all", logging.DEBUG), ("warnings", logging.WARNING), ("errors", logging.ERROR))


class LogBridge(QObject, logging.Handler):
    """A logging.Handler that re-emits records as a signal (queued to the GUI thread)."""

    record = Signal(str, int)

    def __init__(self) -> None:
        QObject.__init__(self)
        logging.Handler.__init__(self, logging.INFO)

    def emit(self, record: logging.LogRecord) -> None:  # type: ignore[override]
        with contextlib.suppress(RuntimeError):  # the bridge was deleted during shutdown
            self.record.emit(self.format(record), record.levelno)


class ConsolePanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setAccessibleName(tr("Log"))
        self.level = QComboBox()
        self.level.setAccessibleName(tr("Show"))
        for key, title in (("all", tr("All messages")), ("warnings", tr("Warnings and errors")),
                           ("errors", tr("Errors only"))):  # fmt: skip
            self.level.addItem(title, key)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("Filter the log"))
        self.search.setAccessibleName(tr("Filter the log"))
        copy, clear = QPushButton(tr("Copy")), QPushButton(tr("Clear"))
        copy.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.text.toPlainText()))
        clear.clicked.connect(self.clear)
        bar = QHBoxLayout()
        for widget in (self.level, self.search, copy, clear):
            bar.addWidget(widget, 1 if widget is self.search else 0)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addLayout(bar)
        layout.addWidget(self.text, 1)
        self.records: deque[tuple[str, int]] = deque(maxlen=MAX_RECORDS)
        self.colors: dict[int, str] = {}
        self.bridge = LogBridge()
        self.bridge.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        self.bridge.record.connect(self.append_record)
        self.level.currentIndexChanged.connect(self._refilter)
        self.search.textChanged.connect(self._refilter)

    def attach(self, logger: logging.Logger | None = None) -> None:
        (logger or logging.getLogger("structura")).addHandler(self.bridge)

    def detach(self, logger: logging.Logger | None = None) -> None:
        (logger or logging.getLogger("structura")).removeHandler(self.bridge)

    def _minimum(self) -> int:
        return dict(LEVELS)[str(self.level.currentData())]

    def _shown(self, line: str, level: int) -> bool:
        needle = self.search.text().lower()
        return level >= self._minimum() and (not needle or needle in line.lower())

    def set_colors(self, warning: str, error: str) -> None:
        """Severity colours from the theme (diag.warning, diag.error)."""
        self.colors = {logging.WARNING: warning, logging.ERROR: error}
        self._refilter()

    def _html(self, line: str, level: int) -> str:
        colour = self.colors.get(logging.ERROR if level >= logging.ERROR else level)
        mark = "⛔ " if level >= logging.ERROR else "⚠ " if level >= logging.WARNING else ""
        text = html.escape(mark + line)
        return f'<span style="color:{colour}">{text}</span>' if colour else text

    @Slot(str, int)
    def append_record(self, text: str, level: int) -> None:
        line = f"{time.strftime('%H:%M:%S')}  {text}"
        self.records.append((line, level))
        if self._shown(line, level):
            self.text.appendHtml(self._html(line, level))

    def _refilter(self) -> None:
        self.text.clear()
        shown = [self._html(line, level) for line, level in self.records if self._shown(line, level)]
        if shown:
            self.text.appendHtml("<br>".join(shown))  # one call: thousands of records stay instant

    def clear(self) -> None:
        self.records.clear()
        self.text.clear()

    def info(self, text: str) -> None:
        self.append_record(text, logging.INFO)
