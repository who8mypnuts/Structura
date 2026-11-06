"""ParamForm: the one generator of settings UIs from ParamSpecs (docs/14 §9)."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QLabel, QLineEdit, QSpinBox, QWidget

from ...core.params import ParamSpec, ParamType


def _editor(spec: ParamSpec, value: Any) -> QWidget:
    if spec.type == ParamType.BOOL:
        box = QCheckBox()
        box.setChecked(bool(value))
        return box
    if spec.type == ParamType.ENUM:
        combo = QComboBox()
        combo.addItems(list(spec.choices))
        combo.setCurrentText(str(value))
        return combo
    if spec.type in (ParamType.INT, ParamType.FLOAT):
        spin: QSpinBox | QDoubleSpinBox = QSpinBox() if spec.type == ParamType.INT else QDoubleSpinBox()
        low, high = spec.range or (-1e9, 1e9)
        if isinstance(spin, QDoubleSpinBox):
            spin.setDecimals(4)
        spin.setRange(low, high)  # type: ignore[arg-type]
        spin.setValue(value)
        return spin
    edit = QLineEdit(str(value))
    return edit


def _value(spec: ParamSpec, widget: QWidget) -> Any:
    if isinstance(widget, QCheckBox):
        return widget.isChecked()
    if isinstance(widget, QComboBox):
        return widget.currentText()
    if isinstance(widget, QSpinBox | QDoubleSpinBox):
        return widget.value()
    assert isinstance(widget, QLineEdit)
    return spec.coerce(widget.text())


class ParamForm(QWidget):
    changed = Signal(str, object)  # key, new value (user edits and set_values alike)

    def __init__(self, specs: tuple[ParamSpec, ...], values: dict[str, Any] | None = None) -> None:
        super().__init__()
        self.specs = specs
        self.form = QFormLayout(self)
        self.widgets: dict[str, QWidget] = {}
        for spec in specs:
            widget = _editor(spec, (values or {}).get(spec.key, spec.default))
            widget.setToolTip(spec.doc or spec.title)
            self.form.addRow(spec.title, widget)
            self.widgets[spec.key] = widget
            _on_change(widget, partial(self._emit, spec.key))

    def _emit(self, key: str, *_signal_args: object) -> None:  # the widget signal's own value is ignored
        self.changed.emit(key, self.value(key))

    def value(self, key: str) -> Any:
        spec = next(s for s in self.specs if s.key == key)
        return _value(spec, self.widgets[key])

    def values(self) -> dict[str, Any]:
        return {s.key: _value(s, self.widgets[s.key]) for s in self.specs}

    def set_values(self, values: dict[str, Any]) -> None:
        """Show new values without emitting ``changed`` (e.g. the script's settings after a build)."""
        for spec in self.specs:
            if spec.key in values:
                widget = self.widgets[spec.key]
                widget.blockSignals(True)
                _set(widget, values[spec.key])
                widget.blockSignals(False)

    def mark(self, key: str, marked: bool, note: str = "") -> None:
        """Flag a row (e.g. 'overridden'): a dot after its label and a note in the tooltip."""
        spec = next(s for s in self.specs if s.key == key)
        label = self.form.labelForField(self.widgets[key])
        if isinstance(label, QLabel):
            label.setText(f"{spec.title} •" if marked else spec.title)
            label.setToolTip(note if marked else "")


def _on_change(widget: QWidget, emit: Callable[[], None]) -> None:
    if isinstance(widget, QCheckBox):
        widget.toggled.connect(emit)
    elif isinstance(widget, QComboBox):
        widget.currentTextChanged.connect(emit)
    elif isinstance(widget, QSpinBox | QDoubleSpinBox):
        widget.valueChanged.connect(emit)
    elif isinstance(widget, QLineEdit):
        widget.editingFinished.connect(emit)


def _set(widget: QWidget, value: Any) -> None:
    if isinstance(widget, QCheckBox):
        widget.setChecked(bool(value))
    elif isinstance(widget, QComboBox):
        widget.setCurrentText(str(value))
    elif isinstance(widget, QSpinBox | QDoubleSpinBox):
        widget.setValue(value)
    elif isinstance(widget, QLineEdit):
        widget.setText(str(value))
