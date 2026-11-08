"""Workspaces (docs/14 §2.1): Code, Explore and Render arrange the same window for different work, and Present
shows only the image. Each workspace remembers the layout the user gave it (dock positions and sizes, the
editor/view split), also across sessions; the first visit uses the workspace's preset."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import QByteArray, QObject, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QWidget

from .dock_layout import BY_TITLE, LAYOUT_VERSION

if TYPE_CHECKING:
    from .app_window import MainWindow


@dataclass(frozen=True)
class Workspace:
    name: str
    shortcut: str
    side: str | None  # the side panel in front (None: the side bar collapsed)
    bottom: bool  # the bottom panels visible
    render_view: bool  # the Render tab in front (else the viewport)
    editor_share: float  # of the central area


WORKSPACES = (
    Workspace("Code", "Ctrl+1", "Outline", True, False, 0.55),
    Workspace("Explore", "Ctrl+2", "Parameters", False, False, 0.30),
    Workspace("Render", "Ctrl+3", "Render Settings", False, True, 0.25),
)
PRESENT = "Present"
BY_NAME = {w.name: w for w in WORKSPACES}


class Workspaces(QObject):
    changed = Signal(str)

    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        self.current = str(window.settings.value("workspaces/current", "Code"))
        if self.current not in BY_NAME:
            self.current = "Code"
        self.presenting: list[QWidget] = []  # what Present hid (restored on leaving)
        self._escape = QShortcut(QKeySequence(Qt.Key.Key_Escape), window)
        self._escape.setEnabled(False)
        self._escape.activated.connect(self.present)

    def reset_layout(self) -> None:
        """View ▸ Reset Layout: every dock where it started, and the workspaces forget their layouts."""
        for ws in WORKSPACES:
            for what in ("state", "split"):
                self.w.settings.set_value(self._key(ws.name, what), None)
        self.w.panels.restore(self.w.default_layout)
        self.apply_preset(BY_NAME[self.current])

    def _key(self, name: str, what: str) -> str:
        return f"workspaces/{name.lower()}/{what}"

    def save_current(self) -> None:
        if not self.presenting:
            self.w.settings.set_value(self._key(self.current, "state"), self.w.saveState(LAYOUT_VERSION))
            self.w.settings.set_value(self._key(self.current, "split"), self.w.split.saveState())

    def switch(self, name: str) -> None:
        """Leave the current workspace (keeping its layout) and arrange the window for ``name``."""
        if self.presenting:
            self.present()
        if name == self.current:
            return
        self.save_current()
        self.current = name
        self.w.settings.set_value("workspaces/current", name)
        if not self._restore(name):
            self.apply_preset(BY_NAME[name])
        self.changed.emit(name)

    def _restore(self, name: str) -> bool:
        state, split = self.w.settings.value(self._key(name, "state")), self.w.settings.value(self._key(name, "split"))
        if not isinstance(state, QByteArray) or not self.w.panels.restore(state):
            return False
        if isinstance(split, QByteArray):
            self.w.split.restoreState(split)
        self.w.views.setCurrentWidget(self.w.render_view if BY_NAME[name].render_view else self.w.viewport)
        return True

    def apply_preset(self, ws: Workspace) -> None:
        panels = self.w.panels
        for title, dock in panels.docks.items():
            if not BY_TITLE[title].side:
                dock.setVisible(ws.bottom)
        if ws.side is None:
            for title, dock in panels.docks.items():
                if BY_TITLE[title].side:
                    dock.hide()
        else:
            panels.show(ws.side)
        if ws.bottom:
            panels.show("Problems")
        self.w.views.setCurrentWidget(self.w.render_view if ws.render_view else self.w.viewport)
        width = max(1, self.w.split.width())
        self.w.split.setSizes([round(width * ws.editor_share), width - round(width * ws.editor_share)])

    # -- Present -------------------------------------------------------------------------------------------
    def present(self) -> None:
        """Only the viewport or render, full screen (Esc or the command again returns)."""
        if self.presenting:
            for widget in self.presenting:
                widget.show()
            self.presenting = []
            self.w.showNormal()
            self._escape.setEnabled(False)
            self.changed.emit(self.current)
            return
        chrome = [self.w.menuBar(), self.w.header, self.w.statusBar(), self.w.rail, self.w.editor_area,
                  self.w.views.tabBar(), self.w.banner, *self.w.panels.docks.values()]  # fmt: skip
        self.presenting = [widget for widget in chrome if widget.isVisible()]
        for widget in self.presenting:
            widget.hide()
        self.w.showFullScreen()
        self._escape.setEnabled(True)
        self.changed.emit(PRESENT)
