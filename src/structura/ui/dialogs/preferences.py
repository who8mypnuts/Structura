"""Preferences (docs/14 §7), generated from ParamSpecs like every other settings UI, in sections: General,
Appearance, Editor, Viewport, Rendering, Paths, Advanced (with Reset Layout and Clear Caches)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import platformdirs
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...compute.select import NAMES
from ...core.params import ParamSpec, ParamType
from ...services.settings import SettingsService
from ...themes.loader import theme_ids
from ..editor.options import option_specs
from ..i18n import available, tr
from ..render_view.presets import PRESETS
from ..session_actions import SPECS as SESSION_SPECS
from ..widgets.param_form import ParamForm

CACHES = ("numba", "skl_numba", "cuda", "thumbnails", "icons")  # folders of the user cache directory


def _specs() -> dict[str, tuple[ParamSpec, ...]]:
    threads = os.cpu_count() or 1
    return {
        "General": (
            *SESSION_SPECS,
            ParamSpec("appearance/language", ParamType.ENUM, "system", "Language (restart)",
                      choices=tuple(available())),
        ),
        "Appearance": (
            ParamSpec("appearance/theme", ParamType.ENUM, "structura-dark", "Theme", choices=tuple(theme_ids())),
            ParamSpec("appearance/follow_system", ParamType.BOOL, False,
                      "Follow the system's light/dark setting (switches to the theme's pair)"),
            ParamSpec("appearance/ui_font", ParamType.ENUM, "Inter", "Interface font", choices=("Inter", "System")),
            ParamSpec("appearance/ui_size", ParamType.INT, 10, "Interface font size", range=(7, 24)),
            ParamSpec("appearance/density", ParamType.ENUM, "comfortable", "Density",
                      choices=("comfortable", "compact")),
            ParamSpec("appearance/reduce_motion", ParamType.BOOL, False, "Reduce motion (no fades or animations)"),
        ),
        "Editor": (
            ParamSpec("editor/code_font", ParamType.STRING, "JetBrains Mono",
                      "Code font (any installed monospace font)"),
            *option_specs(),
            ParamSpec("editor/live_build", ParamType.BOOL, True, "Rebuild while typing"),
        ),
        "Viewport": (
            ParamSpec("viewport/controls", ParamType.ENUM, "structura", "Viewport controls",
                      choices=("structura", "legacy", "blender")),
            ParamSpec("viewport/backend", ParamType.ENUM, "auto", "Viewport (restart)", choices=("auto", "gpu", "cpu")),
        ),
        "Rendering": (
            ParamSpec("render/device", ParamType.ENUM, "auto", "Render device", choices=NAMES),
            ParamSpec("render/preset", ParamType.ENUM, "Standard", "Default render preset",
                      choices=tuple(p.name for p in PRESETS)),
            ParamSpec("render/cpu_threads", ParamType.INT, 0, "CPU threads (0 = all cores)", range=(0, threads)),
            ParamSpec("render/memory_guard", ParamType.INT, 80,
                      "Memory guard: refuse renders needing more than this % of free memory", range=(10, 100)),
        ),
        "Paths": (
            ParamSpec("paths/output", ParamType.STRING, "",
                      "Default folder for new files (empty: Documents/Structura)"),
            ParamSpec("paths/library", ParamType.STRING, "",
                      f"Library folders for #include (separated by '{os.pathsep}')"),
            ParamSpec("paths/blender", ParamType.STRING, "",
                      "Blender executable for 'Open in Blender' (empty: find it)"),
        ),
        "Advanced": (
            ParamSpec("advanced/log_level", ParamType.ENUM, "info", "Log level (Console)",
                      choices=("debug", "info", "warning", "error")),
        ),
    }  # fmt: skip


def preference_specs() -> tuple[ParamSpec, ...]:
    return tuple(spec for specs in _specs().values() for spec in specs)


def clear_caches(root: Path | None = None) -> int:
    """Delete the compiled-kernel, CUDA and thumbnail caches; returns how many folders were removed. Kernels
    are compiled again on the next start (or by `structura warmup`)."""
    base = root or Path(platformdirs.user_cache_dir("structura"))
    removed = 0
    for name in CACHES:
        folder = base / name
        if folder.is_dir():
            shutil.rmtree(folder, ignore_errors=True)
            removed += 1
    return removed


class PreferencesDialog(QDialog):
    def __init__(self, settings: SettingsService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Preferences"))
        self.settings = settings
        self.tabs = QTabWidget()
        self.tabs.setAccessibleName(tr("Preference sections"))
        self.forms: list[ParamForm] = []
        titles = {"General": tr("General"), "Appearance": tr("Appearance"), "Editor": tr("Editor"),
                  "Viewport": tr("Viewport"), "Rendering": tr("Rendering"), "Paths": tr("Paths"),
                  "Advanced": tr("Advanced")}  # fmt: skip
        for section, specs in _specs().items():
            form = ParamForm(specs, {s.key: settings.value(s.key, s.default) for s in specs})
            self.forms.append(form)
            page = self._advanced(form) if section == "Advanced" else form
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(page)
            scroll.setAccessibleName(titles[section])
            self.tabs.addTab(scroll, titles[section])
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs, 1)
        layout.addWidget(buttons)
        self.reset_layout_requested = False

    def _advanced(self, form: ParamForm) -> QWidget:
        page = QWidget()
        column = QVBoxLayout(page)
        column.addWidget(form)
        reset, clear = QPushButton(tr("Reset Window Layout")), QPushButton(tr("Clear Caches"))
        reset.setToolTip(tr("Every panel back where it started (on OK)"))
        clear.setToolTip(tr("Compiled kernels, CUDA binaries and example thumbnails; rebuilt when next needed"))
        reset.clicked.connect(self._reset_layout)
        clear.clicked.connect(self._clear_caches)
        self.note = QLabel("")
        self.note.setObjectName("Muted")
        for widget in (reset, clear, self.note):
            column.addWidget(widget)
        column.addStretch(1)
        return page

    def _reset_layout(self) -> None:
        self.reset_layout_requested = True
        self.note.setText(tr("The layout is reset when you press OK."))

    def _clear_caches(self) -> None:
        count = clear_caches()
        self.note.setText(
            tr("{count} cache folders removed; kernels compile again on the next start.").format(count=count)
        )

    def values(self) -> dict[str, object]:
        return {k: v for form in self.forms for k, v in form.values().items()}

    def apply(self) -> None:
        for key, value in self.values().items():
            self.settings.set_value(key, value)
