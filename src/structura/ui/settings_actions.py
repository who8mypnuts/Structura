"""Applying Preferences to the live window (docs/14 §7): theme (optionally following the system's light/dark
setting), fonts and density, editor options, viewport navigation, render defaults and the log level."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, Qt, Slot
from PySide6.QtGui import QGuiApplication

from ..core.jit import set_cpu_threads
from ..core.lang.includes import set_library_paths
from ..themes.loader import load_theme
from ..themes.qss import Fonts
from .dialogs.build_limits import load_limits
from .fonts import choose_families, code_family, ui_family

if TYPE_CHECKING:
    from .app_window import MainWindow

LOG_LEVELS = {"debug": logging.DEBUG, "info": logging.INFO, "warning": logging.WARNING, "error": logging.ERROR}


def system_is_dark() -> bool | None:
    """The platform's colour scheme: True dark, False light, None unknown."""
    scheme = QGuiApplication.styleHints().colorScheme()
    if scheme == Qt.ColorScheme.Unknown:
        return None
    return scheme == Qt.ColorScheme.Dark


def followed_theme(theme_id: str, dark: bool | None) -> str:
    """The theme to show when following the system: the chosen one, or its light/dark pair on a mismatch."""
    meta = load_theme(theme_id).meta
    if dark is None or meta.dark == dark or not meta.pair:
        return theme_id
    return meta.pair


class SettingsActions(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        self._preset: str | None = None
        QGuiApplication.styleHints().colorSchemeChanged.connect(self._scheme_changed)

    def value(self, key: str, default: object) -> Any:
        return self.w.settings.value(key, default)

    def fonts(self) -> Fonts:
        ui_size, code_size = int(self.value("appearance/ui_size", 10)), int(self.value("editor/code_size", 11))
        return Fonts(ui=ui_family(), ui_size=ui_size, code=code_family(), code_size=code_size)

    def density(self) -> str:
        return str(self.value("appearance/density", "comfortable"))

    def apply(self) -> None:
        """Push stored preferences into the live UI (called at start-up and after Preferences)."""
        w = self.w
        choose_families(str(self.value("appearance/ui_font", "Inter")), str(self.value("editor/code_font", "")))
        w.themes.set_theme(self._theme_id())
        w.workbench.live = bool(self.value("editor/live_build", True))
        w.workbench.limits = load_limits(w.settings)
        w.render_view.device.setCurrentText(str(self.value("render/device", "auto")))
        w.editor_actions.apply()
        w.build_actions.apply_overlays()
        set_cpu_threads(int(self.value("render/cpu_threads", 0)))
        folders = str(self.value("paths/library", "")).split(os.pathsep)
        set_library_paths([Path(f.strip()) for f in folders if f.strip()])
        w.viewport.set_navigation(str(self.value("viewport/controls", "structura")))
        w.viewport.animate_moves = lambda: not bool(self.value("appearance/reduce_motion", False))
        logging.getLogger("structura").setLevel(LOG_LEVELS.get(str(self.value("advanced/log_level", "info")), 20))
        self._apply_preset()
        w.apply_theme(w.themes.theme)

    def _theme_id(self) -> str:
        chosen = str(self.value("appearance/theme", self.w.themes.theme.meta.id))
        if not bool(self.value("appearance/follow_system", False)):
            return chosen
        return followed_theme(chosen, system_is_dark())

    def _apply_preset(self) -> None:
        """The default render preset, set when the preference changes (not over the user's current pick)."""
        preset = str(self.value("render/preset", "Standard"))
        if preset != self._preset:
            self._preset = preset
            self.w.render_view.controls.preset.setCurrentText(preset)

    @Slot(Qt.ColorScheme)
    def _scheme_changed(self, _scheme: Qt.ColorScheme) -> None:
        if bool(self.value("appearance/follow_system", False)):
            self.w.themes.set_theme(followed_theme(self.w.themes.theme.meta.id, system_is_dark()))
