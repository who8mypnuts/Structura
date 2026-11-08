"""Preferences (docs/14 §7), generated from ParamSpecs like every other settings UI."""

from __future__ import annotations

import os

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QWidget

from ...compute.select import NAMES
from ...core.params import ParamSpec, ParamType
from ...services.settings import SettingsService
from ...themes.loader import theme_ids
from ..editor.options import option_specs
from ..i18n import available, tr
from ..session_actions import SPECS as SESSION_SPECS
from ..widgets.param_form import ParamForm


def preference_specs() -> tuple[ParamSpec, ...]:
    return (
        ParamSpec("appearance/theme", ParamType.ENUM, "structura-dark", "Theme", choices=tuple(theme_ids())),
        ParamSpec("appearance/ui_size", ParamType.INT, 10, "Interface font size", range=(7, 24)),
        ParamSpec("appearance/reduce_motion", ParamType.BOOL, False, "Reduce motion (no fades or animations)"),
        ParamSpec("appearance/language", ParamType.ENUM, "system", "Language (restart)", choices=tuple(available())),
        *option_specs(),
        *SESSION_SPECS,
        ParamSpec("editor/live_build", ParamType.BOOL, True, "Rebuild while typing"),
        ParamSpec(
            "viewport/controls",
            ParamType.ENUM,
            "structura",
            "Viewport controls",
            choices=("structura", "legacy", "blender"),
        ),
        ParamSpec("viewport/backend", ParamType.ENUM, "auto", "Viewport (restart)", choices=("auto", "gpu", "cpu")),
        ParamSpec("render/device", ParamType.ENUM, "auto", "Render device", choices=NAMES),
        ParamSpec(
            "render/cpu_threads", ParamType.INT, 0, "CPU threads (0 = all cores)", range=(0, os.cpu_count() or 1)
        ),
        ParamSpec("paths/output", ParamType.STRING, "", "Default folder for new files (empty: Documents/Structura)"),
    )


class PreferencesDialog(QDialog):
    def __init__(self, settings: SettingsService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Preferences"))
        self.settings = settings
        self.specs = preference_specs()
        values = {s.key: settings.value(s.key, s.default) for s in self.specs}
        self.form = ParamForm(self.specs, values)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self.form)
        layout.addWidget(buttons)

    def apply(self) -> None:
        for key, value in self.form.values().items():
            self.settings.set_value(key, value)
