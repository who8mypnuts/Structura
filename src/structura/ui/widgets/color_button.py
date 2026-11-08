"""A button that shows a colour and picks a new one (docs/14 §9 widgets)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import QColorDialog, QPushButton, QWidget


class ColorButton(QPushButton):
    changed = Signal(QColor)

    def __init__(self, color: QColor | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.color = color or QColor("#ffffff")
        self.clicked.connect(self.pick)
        self.set_color(self.color)

    def set_color(self, color: QColor) -> None:
        self.color = QColor(color)
        swatch = QPixmap(28, 14)
        swatch.fill(self.color)
        self.setIcon(QIcon(swatch))
        self.setText(self.color.name())
        self.setAccessibleName(self.color.name())

    def pick(self) -> None:
        """Live while the dialog is open; Cancel goes back to the colour it started with."""
        original = QColor(self.color)
        dialog = QColorDialog(self.color, self)
        dialog.currentColorChanged.connect(self._chosen)
        dialog.colorSelected.connect(self._chosen)
        dialog.rejected.connect(lambda: self._chosen(original))
        dialog.finished.connect(dialog.deleteLater)
        dialog.open()

    def _chosen(self, color: QColor) -> None:
        if color.isValid() and color != self.color:
            self.set_color(color)
            self.changed.emit(color)
