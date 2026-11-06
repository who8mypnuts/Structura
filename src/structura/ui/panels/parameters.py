"""Parameters panel: sliders for '#define NAME V (float:A-B)' GUI parameters (docs/05 §2.2, docs/14 §3)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QSlider, QWidget

from ...core.lang.legacy.preprocessor import GuiParameter

STEPS = 1000


class _ParamRow(QWidget):
    changed = Signal(str, float)

    def __init__(self, param: GuiParameter, value: float) -> None:
        super().__init__()
        self.param = param
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, STEPS)
        self.spin = QDoubleSpinBox()
        self.spin.setDecimals(0 if param.kind == "int" else 2)
        self.spin.setRange(param.minimum, param.maximum)
        self.spin.setValue(value)
        self.slider.setValue(self._to_slider(value))
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.spin)
        self.slider.valueChanged.connect(lambda v: self.spin.setValue(self._from_slider(v)))
        self.spin.valueChanged.connect(self._spin_changed)

    def _to_slider(self, value: float) -> int:
        span = self.param.maximum - self.param.minimum or 1.0
        return round((value - self.param.minimum) / span * STEPS)

    def _from_slider(self, position: int) -> float:
        value = self.param.minimum + (self.param.maximum - self.param.minimum) * position / STEPS
        return float(round(value)) if self.param.kind == "int" else value

    def _spin_changed(self, value: float) -> None:
        self.slider.blockSignals(True)
        self.slider.setValue(self._to_slider(value))
        self.slider.blockSignals(False)
        self.changed.emit(self.param.name, value)


def _empty_label() -> QLabel:
    label = QLabel("No parameters. Declare one with  #define NAME 1 (float:0-2)")
    label.setObjectName("Muted")
    label.setWordWrap(True)  # a long hint must not set the dock's minimum width
    return label


class ParametersPanel(QWidget):
    changed = Signal(str, float)  # name, value

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.form = QFormLayout(self)
        self.empty = _empty_label()
        self.form.addRow(self.empty)
        self._signature: tuple[tuple[str, str, float, float], ...] = ()

    def show_parameters(self, params: tuple[GuiParameter, ...], values: dict[str, float]) -> None:
        signature = tuple((p.name, p.kind, p.minimum, p.maximum) for p in params)
        if signature == self._signature:
            return  # unchanged declarations: keep the widgets (and any drag in progress)
        self._signature = signature
        while self.form.rowCount():
            self.form.removeRow(0)
        if not params:
            self.empty = _empty_label()
            self.form.addRow(self.empty)
        for p in params:
            row = _ParamRow(p, values.get(p.name, p.default))
            row.changed.connect(self.changed)
            self.form.addRow(p.name, row)
