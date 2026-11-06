"""ParamForm: the one generator of settings UIs from ParamSpecs (docs/14 §9)."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QLineEdit, QSpinBox, QWidget

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
    def __init__(self, specs: tuple[ParamSpec, ...], values: dict[str, Any] | None = None) -> None:
        super().__init__()
        self.specs = specs
        layout = QFormLayout(self)
        self.widgets: dict[str, QWidget] = {}
        for spec in specs:
            widget = _editor(spec, (values or {}).get(spec.key, spec.default))
            widget.setToolTip(spec.doc or spec.title)
            layout.addRow(spec.title, widget)
            self.widgets[spec.key] = widget

    def values(self) -> dict[str, Any]:
        return {s.key: _value(s, self.widgets[s.key]) for s in self.specs}
