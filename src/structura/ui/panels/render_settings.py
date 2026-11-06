"""Render Settings panel (docs/14 §3), generated from render_param_specs(). It shows the script's values
after each build (legacy 'set raytracer::…' and v2 blocks) and the user's edits override them."""

from __future__ import annotations

from dataclasses import asdict, replace

from PySide6.QtWidgets import QVBoxLayout, QWidget

from ...render.settings import RenderSettings, render_param_specs
from ..widgets.param_form import ParamForm


class RenderSettingsPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.specs = render_param_specs()
        self.layout_ = QVBoxLayout(self)
        self.form = ParamForm(self.specs)
        self.layout_.addWidget(self.form)
        self.layout_.addStretch(1)

    def show_settings(self, settings: RenderSettings) -> None:
        values = asdict(settings)
        self.layout_.removeWidget(self.form)
        self.form.deleteLater()
        self.form = ParamForm(self.specs, {s.key: values[s.key] for s in self.specs})
        self.layout_.insertWidget(0, self.form)

    def apply(self, settings: RenderSettings) -> RenderSettings:
        return replace(settings, **self.form.values())
