"""Parameters panel: sliders for '#define NAME V (float:A-B)' GUI parameters (docs/05 §2.2, docs/14 §3)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFormLayout, QHBoxLayout, QLabel, QToolButton, QWidget

from ...core.animation.timeline import Timeline
from ...core.lang.legacy.preprocessor import GuiParameter
from ..i18n import tr
from ..widgets.param_slider import ParamSlider


def _key_button(name: str) -> QToolButton:
    button = QToolButton()
    button.setObjectName(f"key:{name}")
    button.setCheckable(True)
    button.setAutoRaise(True)
    button.setText("◇")
    button.setToolTip(f"Key '{name}' at the current frame (Timeline)")
    return button


def _empty_label() -> QLabel:
    label = QLabel(tr("No parameters. Declare one with  #define NAME 1 (float:0-2)"))
    label.setObjectName("Muted")
    label.setWordWrap(True)  # a long hint must not set the dock's minimum width
    return label


class ParametersPanel(QWidget):
    changed = Signal(str, float)  # name, value
    key_toggled = Signal(str)  # name: add or remove its key at the current frame

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
            self.form.addRow(p.name, self._row(p, values.get(p.name, p.default)))

    def _row(self, param: GuiParameter, value: float) -> QWidget:
        slider = ParamSlider(param, value)
        slider.changed.connect(self.changed)
        key = _key_button(param.name)
        key.clicked.connect(lambda _=False, name=param.name: self.key_toggled.emit(name))
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(slider, 1)
        layout.addWidget(key)
        return row

    def show_keys(self, timeline: Timeline, frame: int) -> None:
        """◆ where the parameter has a key at ``frame``, ◈ where it is animated, ◇ otherwise."""
        for button in self.findChildren(QToolButton):
            if not button.objectName().startswith("key:"):
                continue
            name = button.objectName().removeprefix("key:")
            target = f"param:{name}"
            keyed, animated = timeline.has_key(target, frame), timeline.track(target) is not None
            button.blockSignals(True)
            button.setChecked(keyed)
            button.setText("◆" if keyed else ("◈" if animated else "◇"))
            button.blockSignals(False)

    def set_value(self, name: str, value: float) -> None:
        """Mirror a value changed elsewhere (the editor's inline slider) without emitting."""
        for row in self.findChildren(ParamSlider):
            if row.param.name == name:
                row.set_value(value)
