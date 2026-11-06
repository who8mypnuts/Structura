"""ThemeService: the active theme and live switching (docs/13 §5)."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from ..themes.loader import DEFAULT_THEME, load_theme, theme_ids
from ..themes.model import Theme, ThemeMeta
from .settings import SettingsService

KEY = "appearance/theme"


class ThemeService(QObject):
    theme_changed = Signal(object)  # Theme

    def __init__(self, settings: SettingsService) -> None:
        super().__init__()
        self.settings = settings
        self.theme: Theme = load_theme(str(settings.value(KEY, DEFAULT_THEME)))

    def themes(self) -> list[ThemeMeta]:
        return [load_theme(i).meta for i in theme_ids()]

    def set_theme(self, theme_id: str) -> None:
        theme = load_theme(theme_id)
        if theme.meta.id == self.theme.meta.id:
            return
        self.theme = theme
        self.settings.set_value(KEY, theme.meta.id)
        self.theme_changed.emit(theme)

    def toggle_kind(self) -> None:
        """Switch to the paired light/dark counterpart."""
        if self.theme.meta.pair:
            self.set_theme(self.theme.meta.pair)
