"""The window's dialogs and appearance commands: preferences, theme picker / editor, keyboard shortcuts,
light/dark toggle, full screen and About."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QDialog, QMessageBox

from .. import __version__
from .dialogs.keymap_editor import KeymapEditor
from .dialogs.preferences import LIVE_PREFIXES, PreferencesDialog
from .dialogs.theme_editor import ThemeEditor
from .dialogs.theme_picker import ThemePicker

if TYPE_CHECKING:
    from .app_window import MainWindow


class DialogActions(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window

    def preferences(self) -> None:
        """Appearance and editor choices show in the window while the dialog is open; Cancel puts them back."""
        dialog = PreferencesDialog(self.w.settings, self.w)
        before = {key: value for key, value in dialog.values().items() if key.startswith(LIVE_PREFIXES)}
        dialog.previewed.connect(self._preview)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            dialog.apply()
            self.w.apply_settings()
            if dialog.reset_layout_requested:
                self.w.workspaces.reset_layout()
            return
        for key, value in before.items():
            self.w.settings.set_value(key, value)
        self.w.apply_settings()

    def _preview(self, key: str, value: object) -> None:
        self.w.settings.set_value(key, value)
        self.w.apply_settings()

    def choose_theme(self) -> None:
        ThemePicker(self.w.themes, self.w).exec()

    def edit_theme(self) -> None:
        ThemeEditor(self.w.themes, self.w).exec()

    def edit_keymap(self) -> None:
        KeymapEditor(self.w.keymap, self.w).exec()

    def toggle_theme(self) -> None:
        self.w.themes.toggle_kind()

    def toggle_fullscreen(self) -> None:
        if self.w.isFullScreen():
            self.w.showNormal()
        else:
            self.w.showFullScreen()

    def about(self) -> None:
        text = f"Structura {__version__}\nA generative structure editor and renderer.\nMIT licence."
        QMessageBox.about(self.w, "About Structura", text)
