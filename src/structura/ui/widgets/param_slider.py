"""ParamSlider: a GUI parameter's slider (docs/05 §2.2). The Parameters panel shows it with a spin box; the
editor shows a compact one after the declaring line. set_value never emits, so views can mirror each other."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDoubleSpinBox, QHBoxLayout, QLabel, QSlider, QWidget

from ...core.lang.legacy.preprocessor import GuiParameter

STEPS = 1000
COMPACT_WIDTH = 150


class ParamSlider(QWidget):
    changed = Signal(str, float)

    def __init__(self, param: GuiParameter, value: float, compact: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.param = param
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, STEPS)
        self.spin: QDoubleSpinBox | None = None if compact else QDoubleSpinBox()
        self.label = QLabel() if compact else None
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.slider, 1)
        if self.spin is not None:
            self.spin.setDecimals(0 if param.kind == "int" else 2)
            self.spin.setRange(param.minimum, param.maximum)
            layout.addWidget(self.spin)
            self.spin.valueChanged.connect(self._spin_changed)
        if self.label is not None:
            self.label.setObjectName("Muted")
            layout.addWidget(self.label)
            self.setFixedWidth(COMPACT_WIDTH)
        self.setToolTip(f"{param.name}: {param.minimum:g} … {param.maximum:g}")
        self.set_value(value)
        self.slider.valueChanged.connect(self._slider_moved)

    @property
    def value(self) -> float:
        return self._from_slider(self.slider.value()) if self.spin is None else self.spin.value()

    def set_value(self, value: float) -> None:
        for widget in (self.slider, self.spin):
            if widget is not None:
                widget.blockSignals(True)
        self.slider.setValue(self._to_slider(value))
        if self.spin is not None:
            self.spin.setValue(value)
        if self.label is not None:
            self.label.setText(self._text(value))
        for widget in (self.slider, self.spin):
            if widget is not None:
                widget.blockSignals(False)

    def _text(self, value: float) -> str:
        return f"{value:.0f}" if self.param.kind == "int" else f"{value:.2f}"

    def _to_slider(self, value: float) -> int:
        span = self.param.maximum - self.param.minimum or 1.0
        return round((value - self.param.minimum) / span * STEPS)

    def _from_slider(self, position: int) -> float:
        value = self.param.minimum + (self.param.maximum - self.param.minimum) * position / STEPS
        return float(round(value)) if self.param.kind == "int" else value

    def _slider_moved(self, position: int) -> None:
        value = self._from_slider(position)
        if self.spin is not None:
            self.spin.setValue(value)  # emits through _spin_changed
            return
        if self.label is not None:
            self.label.setText(self._text(value))
        self.changed.emit(self.param.name, value)

    def _spin_changed(self, value: float) -> None:
        self.slider.blockSignals(True)
        self.slider.setValue(self._to_slider(value))
        self.slider.blockSignals(False)
        self.changed.emit(self.param.name, value)
