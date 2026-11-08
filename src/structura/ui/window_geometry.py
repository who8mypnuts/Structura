"""The main window's size and placement (docs/14 §2): the default size, the first dock sizes and editor split,
and keeping the window on its screen."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QSize, Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget

if TYPE_CHECKING:
    from .app_window import MainWindow

DEFAULT_SIZE = QSize(1440, 900)
EDITOR_SHARE = 0.45  # of the central area, beside the viewport
SCREEN_FRACTION = 0.92  # leave room for panels and window decorations
SIDE_WIDTH = 280  # the side panel beside the activity rail
BOTTOM_HEIGHT = 170


def initial_size(widget: QWidget) -> QSize:
    """The default window size, shrunk to fit the screen the window opens on."""
    screen = widget.screen() or QGuiApplication.primaryScreen()
    if screen is None:
        return DEFAULT_SIZE
    room = screen.availableGeometry().size() * SCREEN_FRACTION
    return DEFAULT_SIZE.boundedTo(room)


class WindowGeometry(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        self.sized = False  # the default dock sizes were applied (or a saved layout restored)
        self.split_sized = False  # the editor/view split was set (or restored)

    def shown(self) -> None:
        """The window was shown: fit it to the screen, then apply the first-run sizes once."""
        QTimer.singleShot(0, self.fit_to_screen)
        if not self.sized:  # dock sizes only apply once the window has its real geometry
            self.sized = True
            QTimer.singleShot(0, self.initial_dock_sizes)
        if not self.split_sized:
            self.split_sized = True
            QTimer.singleShot(0, lambda: QTimer.singleShot(0, self.initial_split))  # after the dock sizes

    def fit_to_screen(self) -> None:
        """Keep the (normal, not maximised) window on its screen: a layout saved by an earlier version, or a dock
        that asked for more height, must never leave the bottom of the window out of reach."""
        w = self.w
        screen = w.screen()
        if screen is None or w.isFullScreen() or w.isMaximized():
            return
        room, frame = screen.availableGeometry(), w.frameGeometry()
        if frame.height() <= room.height() and frame.width() <= room.width():
            return
        decoration = frame.height() - w.height()
        w.resize(min(w.width(), room.width()), min(w.height(), room.height() - decoration))
        w.move(max(room.left(), min(w.x(), room.right() - w.width())), max(room.top(), w.y()))

    def initial_dock_sizes(self) -> None:
        # The first layout pass can run before the header has collapsed its labels, which widens the window;
        # Qt never shrinks it back, so the intended size is applied again now that the minimum is final.
        w = self.w
        w.resize(initial_size(w))
        area = Qt.DockWidgetArea.BottomDockWidgetArea
        bottom = [d for d in w.docks.values() if w.dockWidgetArea(d) == area and not d.isHidden()]
        w.resizeDocks(bottom, [BOTTOM_HEIGHT] * len(bottom), Qt.Orientation.Vertical)
        side = [d for d in w.docks.values() if d.isVisible() and d not in bottom]
        w.resizeDocks(side, [SIDE_WIDTH] * len(side), Qt.Orientation.Horizontal)

    def initial_split(self) -> None:
        """Editor and views share the central area 45 : 55 once its width is known."""
        width = max(1, self.w.split.width())
        self.w.split.setSizes([round(width * EDITOR_SHARE), width - round(width * EDITOR_SHARE)])
