"""Toasts (docs/14 §6): short, stackable notices at the bottom right of the window, for finished exports,
saved files and non-critical warnings. A toast can carry one action ("Show in Folder"). They fade in and out
over 150 ms unless the user asked for reduced motion, and never take the keyboard focus."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import shiboken6
from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPropertyAnimation, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QPushButton, QWidget

from ..i18n import tr

SECONDS = 4.0
MAX_TOASTS = 3
MARGIN = 16
FADE_MS = 150


class Toast(QFrame):
    def __init__(self, text: str, action: tuple[str, Callable[[], object]] | None, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("ToastFrame")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.label = QLabel(text)
        self.label.setObjectName("Toast")
        self.label.setWordWrap(True)
        self.label.setMaximumWidth(420)
        self.label.setAccessibleName(text)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label, 1)
        self.button: QPushButton | None = None
        if action is not None:
            self.button = QPushButton(action[0])
            self.button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.button.clicked.connect(action[1])
            self.button.clicked.connect(self.close)
            layout.addWidget(self.button)
        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)


def reveal(path: Path) -> Callable[[], object]:
    """An action that opens the folder containing ``path`` in the file manager."""
    return lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))


class ToastStack(QObject):
    """Owns the toasts of one window and keeps them stacked in its bottom-right corner."""

    def __init__(self, window: QWidget, animate: Callable[[], bool] = lambda: True) -> None:
        super().__init__(window)
        self.window, self.animate = window, animate
        self.toasts: list[Toast] = []
        window.installEventFilter(self)

    def show(self, text: str, action: tuple[str, Callable[[], object]] | None = None) -> Toast:
        toast = Toast(text, action, self.window)
        toast.destroyed.connect(lambda *_: self._forget(toast))
        self.toasts.append(toast)
        while len(self.toasts) > MAX_TOASTS:
            self.toasts.pop(0).deleteLater()
        toast.adjustSize()
        toast.show()
        toast.raise_()
        self._fade(toast, 0.0, 1.0)
        QTimer.singleShot(int(SECONDS * 1000), toast, lambda: self._dismiss(toast))  # toast: cancelled with it
        self._place()
        return toast

    def show_file(self, text: str, path: Path) -> Toast:
        return self.show(text, (tr("Show in Folder"), reveal(path)))

    def _fade(self, toast: Toast, start: float, end: float, then: Callable[[], object] | None = None) -> None:
        if not self.animate():
            toast.effect.setOpacity(end)
            if then is not None:
                then()
            return
        animation = QPropertyAnimation(toast.effect, b"opacity", toast)
        animation.setDuration(FADE_MS)
        animation.setStartValue(start)
        animation.setEndValue(end)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        if then is not None:
            animation.finished.connect(then)
        animation.start()

    def _dismiss(self, toast: Toast) -> None:
        if toast in self.toasts:
            self._fade(toast, 1.0, 0.0, toast.deleteLater)

    def _forget(self, toast: Toast) -> None:
        if toast in self.toasts:
            self.toasts.remove(toast)
            self._place()

    def _place(self) -> None:
        if not shiboken6.isValid(self.window):
            return  # the window is being destroyed (and its toasts with it)
        bottom = self.window.height() - MARGIN - 28  # above the status bar
        for toast in reversed(self.toasts):
            toast.adjustSize()
            bottom -= toast.height()
            toast.move(self.window.width() - toast.width() - MARGIN, bottom)
            bottom -= 8

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if watched is self.window and event.type() == QEvent.Type.Resize:
            self._place()
        return False
