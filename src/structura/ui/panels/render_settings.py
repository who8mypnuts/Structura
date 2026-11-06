"""Render Settings panel (docs/14 §3), generated from render_param_specs(). It shows the script's values
after each build (legacy 'set raytracer::…' and v2 blocks). Values the user edits become **overrides**:
they are kept across rebuilds, marked with a dot, and applied on top of the script's settings, while the
fields the user did not touch keep following the script. "Reset to script" drops the overrides."""

from __future__ import annotations

from dataclasses import asdict, replace
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget

from ...render.settings import RenderSettings, render_param_specs
from ..i18n import tr
from ..widgets.param_form import ParamForm

NOTE = "Overrides the script's value (Reset to script to follow the script again)"


class RenderSettingsPanel(QWidget):
    overrides_changed = Signal(dict)  # the current tab keeps them (and project files save them)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.specs = render_param_specs()
        self.form = ParamForm(self.specs)
        self.overrides: dict[str, Any] = {}
        self.reset = QPushButton(tr("Reset to script"))
        self.reset.setEnabled(False)
        self.reset.clicked.connect(lambda: self.set_overrides({}, emit=True))
        layout = QVBoxLayout(self)
        layout.addWidget(self.form)
        layout.addWidget(self.reset)
        layout.addStretch(1)
        self._script: dict[str, Any] = {}
        self.form.changed.connect(self._edited)

    def show_settings(self, settings: RenderSettings) -> None:
        """The script's settings after a build; overridden fields keep the user's values."""
        values = asdict(settings)
        self._script = {s.key: values[s.key] for s in self.specs}
        self.form.set_values(self._script | self.overrides)

    def set_overrides(self, overrides: dict[str, Any], emit: bool = False) -> None:
        self.overrides = {k: v for k, v in overrides.items() if any(s.key == k for s in self.specs)}
        self.form.set_values(self._script | self.overrides)
        self._mark()
        if emit:
            self.overrides_changed.emit(dict(self.overrides))

    def _edited(self, key: str, value: Any) -> None:
        if self._script.get(key) == value:
            self.overrides.pop(key, None)  # back to the script's value: no longer an override
        else:
            self.overrides[key] = value
        self._mark()
        self.overrides_changed.emit(dict(self.overrides))

    def _mark(self) -> None:
        for spec in self.specs:
            self.form.mark(spec.key, spec.key in self.overrides, NOTE)
        self.reset.setEnabled(bool(self.overrides))

    def apply(self, settings: RenderSettings) -> RenderSettings:
        return replace(settings, **self.overrides)
