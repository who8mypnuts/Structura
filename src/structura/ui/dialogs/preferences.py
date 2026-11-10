"""Preferences (docs/14 §7), generated from ParamSpecs like every other settings UI, in sections: General,
Appearance, Editor, Viewport, Rendering, Paths, Advanced (with Reset Layout and Clear Caches)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import platformdirs
from PySide6.QtCore import Signal
from PySide6.QtGui import QShowEvent
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


def _path_specs() -> tuple[ParamSpec, ...]:
    """Preferences ▸ Paths: folders, and the other applications Structura opens files in (ui/external_apps)."""
    return (
        ParamSpec("paths/output", ParamType.STRING, "", "Default folder for new files (empty: Documents/Structura)"),
        ParamSpec("paths/library", ParamType.STRING, "", f"Library folders for #include (separated by '{os.pathsep}')"),
        ParamSpec("paths/blender", ParamType.STRING, "", "Blender executable for 'Open in Blender' (empty: find it)"),
        ParamSpec("paths/meshlab", ParamType.STRING, "", "MeshLab executable for 'Open in MeshLab' (empty: find it)"),
    )


def _specs() -> dict[str, tuple[ParamSpec, ...]]:
    """Every preference by section, as ParamSpecs (the dialog is generated from them)."""
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
            ParamSpec("viewport/orbit_lock", ParamType.ENUM, "free", "Orbit lock (one axis while orbiting and panning)",
                      choices=("free", "horizontal", "vertical")),
            ParamSpec("viewport/backend", ParamType.ENUM, "auto",
                      "Viewport engine (restart): auto; gpu = OpenGL even when the start-up check fails; cpu = compute",
                      choices=("auto", "gpu", "cpu")),
        ),
        "Rendering": (
            ParamSpec("render/device", ParamType.ENUM, "auto", "Render device", choices=NAMES),
            ParamSpec("render/preset", ParamType.ENUM, "Standard", "Default render preset",
                      choices=tuple(p.name for p in PRESETS)),
            ParamSpec("render/cpu_threads", ParamType.INT, 0, "CPU threads (0 = all cores)", range=(0, threads)),
            ParamSpec("render/keep_folder", ParamType.STRING, "",
                      "Keep every render: save each finished render with its report into this folder (empty: off)"),
            ParamSpec("render/memory_guard", ParamType.INT, 80,
                      "Memory guard: refuse renders needing more than this % of free memory", range=(10, 100)),
        ),
        "Paths": _path_specs(),
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


LIVE_PREFIXES = ("appearance/", "editor/")  # previewed in the window while the dialog is open


class PreferencesDialog(QDialog):
    """Preferences in sections, generated from ParamSpecs; appearance and editor changes are previewed."""

    previewed = Signal(str, object)  # an appearance or editor preference changed: show it at once

    def __init__(self, settings: SettingsService, parent: QWidget | None = None) -> None:
        """Builds a form per section from the stored values.

        Args:
            settings: The preferences.
            parent: The parent widget.
        """
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
            form.changed.connect(self._changed)
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
        self._sized = False

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._sized:  # once, with the window's fonts and style applied (the hints are final then)
            self._sized = True
            self._size_to_content()

    def _size_to_content(self) -> None:
        """Wide enough for every tab title and the widest page, tall enough for the tallest page (a tab widget
        sizes itself to the first page alone, which squashed the dialog)."""
        pages = [self.tabs.widget(i).widget() for i in range(self.tabs.count())]  # type: ignore[union-attr]
        width = max(self.tabs.tabBar().sizeHint().width() + 48, *(p.sizeHint().width() + 72 for p in pages), 640)
        height = max(*(p.sizeHint().height() + 140 for p in pages), 420)
        screen = self.screen().availableGeometry() if self.screen() else None
        if screen is not None:
            width, height = min(width, screen.width() - 80), min(height, screen.height() - 80)
        self.resize(width, height)

    def _changed(self, key: str, value: object) -> None:
        if key.startswith(LIVE_PREFIXES):
            self.previewed.emit(key, value)

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
