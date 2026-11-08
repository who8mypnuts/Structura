"""The welcome page (docs/14 §5.1): shown in the editor area while no script is open. Start (new, open,
examples), recent files, four theme thumbnails, and the render device Structura found."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..services.jobs import FunctionJob, JobContext, JobRunner, Lane
from ..services.render import DeviceBackends
from ..themes.loader import load_theme
from .header import BRAND
from .i18n import tr

THEMES = ("structura-dark", "structura-light", "nord", "nord-light")
RECENT_SHOWN = 8
MAX_WIDTH = 360


THUMB = (132, 84)


def theme_thumbnail(theme_id: str) -> QIcon:
    """A tiny drawing of the theme: window, editor with three coloured code lines, accent bar."""
    theme, size = load_theme(theme_id), QSize(*THUMB)
    pixmap = QPixmap(size)
    pixmap.fill(QColor(theme["ui.bg"][:7]))
    p = QPainter(pixmap)
    w, h = size.width(), size.height()
    p.fillRect(0, 0, w, 12, QColor(theme["toolbar.bg"][:7]))
    p.fillRect(8, 20, w // 2, h - 28, QColor(theme["editor.bg"][:7]))
    for n, role in enumerate(("syntax.keyword", "syntax.number", "syntax.string")):
        p.fillRect(14, 28 + n * 12, 24 + 10 * n, 5, QColor(theme[role][:7]))
    p.fillRect(w // 2 + 14, 20, w // 2 - 22, h - 28, QColor(theme["viewport.bg.top"][:7]))
    p.fillRect(0, h - 4, w, 4, QColor(theme["ui.accent"][:7]))
    p.end()
    return QIcon(pixmap)


def _device_probe(backends: DeviceBackends) -> Callable[[JobContext], tuple[str, bool]]:
    def run(ctx: JobContext) -> tuple[str, bool]:
        backend = backends.get("auto")  # on the device lane, where renders create it too
        return f"{backend.name.upper()} {backend.device_name}".strip(), backend.is_gpu

    return run


class WelcomePage(QScrollArea):
    new_script = Signal()
    open_file = Signal()
    open_recent = Signal(Path)
    show_examples = Signal()
    choose_theme = Signal(str)

    def __init__(self, recent: Callable[[], list[Path]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Welcome")
        self.setAccessibleName(tr("Welcome"))
        self.setWidgetResizable(True)
        self.recent_paths = recent
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)
        layout.addLayout(self._title())
        layout.addWidget(self._section(tr("Start")))
        layout.addLayout(self._start_buttons())
        layout.addWidget(self._section(tr("Recent")))
        self.recent_box = QVBoxLayout()
        layout.addLayout(self.recent_box)
        layout.addWidget(self._section(tr("Theme")))
        layout.addLayout(self._themes())
        self.device = QLabel(tr("Looking for a render device…"))
        self.device.setObjectName("Muted")
        layout.addWidget(self.device)
        layout.addStretch(1)
        self.setWidget(body)
        self.refresh()

    def _title(self) -> QHBoxLayout:
        logo = QLabel()
        logo.setPixmap(QPixmap(str(BRAND / "png" / "icon-64.png")).scaledToHeight(48))
        title = QLabel(f"<span style='font-size:22pt; font-weight:600'>Structura</span><br>"
                       f"<span>{tr('Grammar-based 3D structures')}</span><br><span>{__version__}</span>")  # fmt: skip
        title.setWordWrap(True)
        row = QHBoxLayout()
        row.addWidget(logo)
        row.addWidget(title, 1)
        return row

    @staticmethod
    def _section(text: str) -> QLabel:
        label = QLabel(f"<b>{text}</b>")
        label.setObjectName("Brand")
        return label

    def _start_buttons(self) -> QVBoxLayout:
        column = QVBoxLayout()
        actions = ((tr("New Script"), "Ctrl+N", self.new_script), (tr("Open…"), "Ctrl+O", self.open_file),
                   (tr("Browse Examples"), "Ctrl+Shift+X", self.show_examples))  # fmt: skip
        for text, keys, signal in actions:
            button = QPushButton(f"{text}  ·  {keys}")
            button.setAccessibleName(text)
            button.setMaximumWidth(MAX_WIDTH)
            button.setStyleSheet("text-align: left;")
            button.clicked.connect(signal)
            column.addWidget(button)
        return column

    def _themes(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setAlignment(Qt.AlignmentFlag.AlignLeft)
        for n, theme_id in enumerate(THEMES):
            button = QToolButton()
            button.setIcon(theme_thumbnail(theme_id))
            button.setIconSize(QSize(*THUMB))
            button.setText(load_theme(theme_id).meta.name)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setAccessibleName(button.text())
            button.clicked.connect(lambda _=False, t=theme_id: self.choose_theme.emit(t))
            grid.addWidget(button, n // 2, n % 2)
        return grid

    def refresh(self) -> None:
        """Re-list the recent files (they change while the page is hidden)."""
        while self.recent_box.count():
            item = self.recent_box.takeAt(0)
            if item is not None and item.widget() is not None:
                item.widget().deleteLater()  # type: ignore[union-attr]
        paths = self.recent_paths()[:RECENT_SHOWN]
        if not paths:
            self.recent_box.addWidget(QLabel(tr("No recent files yet.")))
        for path in paths:
            button = QPushButton(path.name)
            button.setToolTip(str(path))
            button.setFlat(True)
            button.setMaximumWidth(MAX_WIDTH)
            button.setStyleSheet("text-align: left;")
            button.setAccessibleName(path.name)
            button.clicked.connect(lambda _=False, p=path: self.open_recent.emit(p))
            self.recent_box.addWidget(button)

    def probe_device(self, runner: JobRunner, backends: DeviceBackends) -> None:
        handle = runner.submit(FunctionJob("probe device", Lane.DEVICE, _device_probe(backends), key="probe device"))
        handle.finished.connect(self._device_found)

    def _device_found(self, result: object) -> None:
        if isinstance(result, tuple):
            name, gpu = result
            text = tr("GPU rendering: {device} ✓") if gpu else tr("CPU rendering: {cores} cores (no GPU compute)")
            self.device.setText(text.format(device=name, cores=os.cpu_count()))
