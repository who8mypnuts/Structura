"""The controls of v2's non-numeric #param kinds (docs/05 §9.2, docs/14 §3): a colour button, a switch or a
choice list. Like ParamSlider they report a float (0xRRGGBB, 1 / 0, the choice's index) and set_value never
emits, so the Parameters panel treats every parameter alike."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QWidget

from ...core.lang.legacy.preprocessor import GuiParameter
from .color_button import ColorButton


class ParamChoice(QWidget):
    changed = Signal(str, float)
    released = Signal(str)  # (never: these controls have no drag)
    dragging = False

    def __init__(self, param: GuiParameter, value: float, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.param = param
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.control: QWidget
        if param.kind == "color":
            self.control = ColorButton()
            self.control.changed.connect(lambda c: self._emit(float(c.rgb() & 0xFFFFFF)))
        elif param.kind == "bool":
            self.control = QCheckBox()
            self.control.toggled.connect(lambda on: self._emit(1.0 if on else 0.0))
        else:
            self.control = QComboBox()
            self.control.addItems(list(param.choices))
            self.control.currentIndexChanged.connect(lambda i: self._emit(float(i)))
        self.control.setAccessibleName(param.name)
        layout.addWidget(self.control)
        layout.addStretch(1)
        self.set_value(value)

    def _emit(self, value: float) -> None:
        self.changed.emit(self.param.name, value)

    def set_value(self, value: float) -> None:
        self.control.blockSignals(True)
        if isinstance(self.control, ColorButton):
            self.control.set_color(QColor(f"#{int(value) & 0xFFFFFF:06x}"))
        elif isinstance(self.control, QCheckBox):
            self.control.setChecked(value >= 0.5)
        elif isinstance(self.control, QComboBox):
            self.control.setCurrentIndex(round(value))
        self.control.blockSignals(False)
