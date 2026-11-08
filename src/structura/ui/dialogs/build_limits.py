"""Build ▸ Build Limits… (docs/14 §4.1, docs/06 §10.2): caps every build of this window on top of the
script's own 'set maxobjects' and 'set maxdepth' — an object limit, a time limit and the memory guard."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget

from ...core.params import ParamSpec, ParamType
from ...services.build import BuildLimits
from ...services.settings import SettingsService
from ..i18n import tr
from ..widgets.param_form import ParamForm

SPECS = (
    ParamSpec("build/max_objects", ParamType.INT, 0, "Object limit (0 = the script's)", range=(0, 1_000_000_000)),
    ParamSpec("build/time_limit", ParamType.FLOAT, 0.0, "Time limit, s (0 = none)", range=(0.0, 86_400.0)),
    ParamSpec("build/memory_guard", ParamType.INT, 50, "Memory guard, % of the free memory", range=(5, 95)),
)


def load_limits(settings: SettingsService) -> BuildLimits:
    value = {s.key: settings.value(s.key, s.default) for s in SPECS}
    return BuildLimits(int(value["build/max_objects"]), int(value["build/memory_guard"]),
                       float(value["build/time_limit"]))  # fmt: skip


class BuildLimitsDialog(QDialog):
    def __init__(self, settings: SettingsService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Build Limits"))
        self.settings = settings
        self.form = ParamForm(SPECS, {s.key: settings.value(s.key, s.default) for s in SPECS})
        note = QLabel(tr("A build that reaches a limit stops there and shows what it has built so far."))
        note.setObjectName("Muted")
        note.setWordWrap(True)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        for widget in (self.form, note, buttons):
            layout.addWidget(widget)

    def apply(self) -> BuildLimits:
        for key, value in self.form.values().items():
            self.settings.set_value(key, value)
        return load_limits(self.settings)
