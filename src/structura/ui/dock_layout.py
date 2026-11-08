"""Dock panels and the activity rail (docs/14 §2).

The side panels (Examples, Outline, Parameters, …) are not tabified: a slim vertical *activity rail* at the
window's left edge shows one of them at a time, like VS Code's activity bar. The rail has an icon per panel
with the name in its tooltip, and the panel's title bar shows the name at full size. No tab is ever
squeezed until its label is unreadable. Clicking the active panel's icon collapses the side bar.

The bottom panels stay tabified, with their tabs at the top. A tabified dock hides its own title bar,
because the tab already names it, so there is one readable header instead of two. Every dock can still be
dragged, floated and restored.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QByteArray, QObject, QSize, Qt, QTimer, Slot
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QDockWidget, QMainWindow, QTabWidget, QToolBar, QToolButton, QWidget

from ..themes.model import Theme
from .commands.registry import CommandRegistry
from .i18n import tr
from .icons import icon

LAYOUT_VERSION = 2  # QMainWindow.saveState version; 1 = every side panel tabified (before the rail)
Area = Qt.DockWidgetArea


@dataclass(frozen=True)
class Panel:
    title: str
    glyph: str  # icons.PATHS key
    shortcut: str = ""
    side: bool = True  # True: on the activity rail (left); False: a bottom tab
    hidden: bool = False  # not shown until asked for (View ▸ Panels)

    @property
    def command_id(self) -> str:
        return "view.panel." + self.title.lower().replace(" ", "_")


PANELS = (
    Panel("Files", "folder", "Ctrl+Shift+E"),
    Panel("Examples", "book", "Ctrl+Shift+X"),
    Panel("Outline", "list", "Ctrl+Shift+O"),
    Panel("Parameters", "sliders", "Ctrl+Shift+A"),
    Panel("Camera", "camera", "Ctrl+Shift+K"),
    Panel("Inspector", "info", "Ctrl+Shift+I"),
    Panel("Materials", "sphere"),
    Panel("Lights", "sun"),
    Panel("Variations", "grid"),
    Panel("Render Settings", "aperture", "Ctrl+Shift+G"),
    Panel("Problems", "alert", "Ctrl+Shift+M", side=False),
    Panel("Console", "terminal", "Ctrl+`", side=False),
    Panel("Build Stats", "chart", side=False),
    Panel("Timeline", "film", side=False),
    Panel("Search", "search", side=False),
    Panel("Render Queue", "layers", side=False),
    Panel("History", "clock", side=False),
    Panel("Activity", "activity", side=False, hidden=True),
)
BY_TITLE = {p.title: p for p in PANELS}


class ActivityRail(QToolBar):
    """The vertical icon strip; its buttons are the registry's panel commands (no duplicate actions)."""

    def __init__(self, registry: CommandRegistry, parent: QWidget | None = None) -> None:
        super().__init__(tr("Panels"), parent)
        self.setObjectName("ActivityRail")
        self.setAccessibleName(tr("Panels"))
        self.setOrientation(Qt.Orientation.Vertical)
        self.setMovable(False)
        self.setFloatable(False)
        self.setIconSize(QSize(22, 22))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.registry = registry
        for panel in PANELS:
            if panel.side:
                action = registry.action(panel.command_id)
                self.addAction(action)
                button = self.widgetForAction(action)
                if button is not None:
                    button.setAccessibleName(action.text())
        self.toggleViewAction().setVisible(False)  # the rail is not optional chrome

    def set_theme(self, theme: Theme) -> None:
        """Icons in the theme's colours; tooltips with the current shortcut (the keymap may have changed it)."""
        for panel in PANELS:
            if panel.side:
                action = self.registry.action(panel.command_id)
                action.setIcon(icon(panel.glyph, theme["ui.fg"]))
                keys = action.shortcut().toString(QKeySequence.SequenceFormat.NativeText)
                action.setToolTip(f"{action.text()} ({keys})" if keys else action.text())

    def buttons(self) -> list[QToolButton]:
        return [b for b in self.findChildren(QToolButton) if b.defaultAction() is not None]


class DockLayout(QObject):
    """Creates the docks, keeps one side panel visible at a time and tidies the title bars."""

    def __init__(self, window: QMainWindow) -> None:
        super().__init__(window)
        self.w = window
        self.docks: dict[str, QDockWidget] = {}
        self.rail: ActivityRail | None = None
        self.restoring = False  # restoreState re-applies a saved layout: no one-side-panel rule meanwhile
        window.setTabPosition(Area.AllDockWidgetAreas, QTabWidget.TabPosition.North)
        self._tidy = QTimer(self)
        self._tidy.setSingleShot(True)
        self._tidy.setInterval(0)
        self._tidy.timeout.connect(self.tidy_title_bars)

    def add(self, title: str, widget: QWidget) -> QDockWidget:
        panel = BY_TITLE[title]
        dock = QDockWidget(tr(title, "Panels"), self.w)
        dock.setObjectName(f"dock-{title.lower().replace(' ', '-')}")
        dock.setWidget(widget)
        widget.setAccessibleName(dock.windowTitle())
        area = Area.LeftDockWidgetArea if panel.side else Area.BottomDockWidgetArea
        self.w.addDockWidget(area, dock)
        group = [d for t, d in self.docks.items() if BY_TITLE[t].side == panel.side]
        if panel.side and group:
            dock.hide()  # one side panel at a time; the rail shows the others
        elif group:
            self.w.tabifyDockWidget(group[0], dock)
            group[0].raise_()  # the first bottom panel stays in front
        self.docks[title] = dock
        if panel.hidden:
            dock.hide()
        dock.visibilityChanged.connect(lambda visible, t=title: self._visibility(t, visible))
        dock.topLevelChanged.connect(self._tidy.start)
        dock.dockLocationChanged.connect(self._tidy.start)
        self._tidy.start()
        return dock

    def attach_rail(self, registry: CommandRegistry) -> ActivityRail:
        self.rail = ActivityRail(registry, self.w)
        self.w.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.rail)
        return self.rail

    def restore(self, state: QByteArray) -> bool:
        """QMainWindow.restoreState, without the one-side-panel rule reacting to the intermediate steps."""
        self.restoring = True
        try:
            return bool(self.w.restoreState(state, LAYOUT_VERSION))
        finally:
            self.restoring = False

    # -- showing panels --------------------------------------------------------------------------------------
    def visible(self, title: str) -> bool:
        dock = self.docks.get(title)
        return dock is not None and dock.isVisible()

    def show(self, title: str) -> None:
        dock = self.docks[title]
        dock.show()
        dock.raise_()

    def toggle(self, title: str) -> None:
        """The rail and View ▸ Panels: show a panel, or collapse it when it is already in front."""
        if self.visible(title):
            self.docks[title].hide()
        else:
            self.show(title)

    @Slot()
    def _visibility(self, title: str, visible: bool) -> None:
        dock = self.docks[title]
        if visible and BY_TITLE[title].side and not dock.isFloating() and not self.restoring:
            self._hide_side_siblings(dock)
        self._tidy.start()
        if self.rail is not None:
            self.rail.registry.refresh()

    def _hide_side_siblings(self, dock: QDockWidget) -> None:
        """Hide the other side panels docked in the same area (not the ones the user tabified with it)."""
        area, tabbed = self.w.dockWidgetArea(dock), set(self.w.tabifiedDockWidgets(dock))
        for title, other in self.docks.items():
            if other is dock or not BY_TITLE[title].side or other in tabbed or other.isFloating():
                continue
            if self.w.dockWidgetArea(other) == area and not other.isHidden():
                other.hide()

    # -- title bars --------------------------------------------------------------------------------------------
    @Slot()
    def tidy_title_bars(self) -> None:
        """A docked, tabified panel is named by its tab: its own title bar would repeat the name."""
        for dock in self.docks.values():
            hide = not dock.isFloating() and bool(self.w.tabifiedDockWidgets(dock))
            bar = dock.titleBarWidget()
            if hide and bar is None:
                dock.setTitleBarWidget(QWidget(dock))
            elif not hide and bar is not None:
                dock.setTitleBarWidget(None)  # type: ignore[arg-type]  # nullptr restores the default bar
                bar.deleteLater()
