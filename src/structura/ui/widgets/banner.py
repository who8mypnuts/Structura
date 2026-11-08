"""Banners (docs/14 §6): a strip at the top of a view for a persistent condition, with up to a few actions and
a close button. Unlike toasts they stay until acted on or dismissed."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QToolButton, QWidget

from ..i18n import tr


class Banner(QFrame):
    dismissed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Banner")
        self.label = QLabel()
        self.label.setWordWrap(True)
        self.row = QHBoxLayout(self)
        self.row.setContentsMargins(10, 6, 6, 6)
        self.row.addWidget(self.label, 1)
        self.buttons: list[QPushButton] = []
        close = QToolButton()
        close.setText("✕")
        close.setAccessibleName(tr("Dismiss"))
        close.setToolTip(tr("Dismiss"))
        close.clicked.connect(self.dismiss)
        self.row.addWidget(close)
        self.key = ""  # what the banner is about (one message at a time)
        self.hide()

    def show_message(self, key: str, text: str, actions: tuple[tuple[str, Callable[[], object]], ...] = ()) -> None:
        for button in self.buttons:
            button.deleteLater()
        self.buttons = []
        for title, handler in actions:
            button = QPushButton(title)
            button.clicked.connect(handler)
            button.clicked.connect(self.dismiss)
            self.row.insertWidget(self.row.count() - 1, button)
            self.buttons.append(button)
        self.key = key
        self.label.setText(text)
        self.show()

    def dismiss(self) -> None:
        if self.isVisible():
            self.hide()
            self.dismissed.emit()
