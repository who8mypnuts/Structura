"""Help commands (docs/12 §2.2): F1 opens the language reference at the diagnostic or symbol under the cursor."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject

from ..core.lang.reference import anchor_at, anchors
from .dialogs.reference import ReferenceBrowser
from .editor.quick_fix import diagnostics_at

if TYPE_CHECKING:
    from .app_window import MainWindow


class HelpActions(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        self.browser: ReferenceBrowser | None = None

    def anchor_at_cursor(self) -> str | None:
        tab = self.w.tabs.current()
        if tab is None:
            return None
        position = tab.editor.textCursor().position()
        for d in diagnostics_at(tab.editor, position):
            if f"diag-{d.code}" in anchors() and d.span and d.span.start <= position <= d.span.end:
                return f"diag-{d.code}"
        return anchor_at(tab.text(), position)

    def reference(self) -> None:
        """F1: the reference at the symbol under the cursor (the top when there is nothing to look up)."""
        if self.browser is None:
            self.browser = ReferenceBrowser(self.w.themes.theme, self.w)
            self.w.themes.theme_changed.connect(self.browser.set_theme)
        self.browser.show_anchor(self.anchor_at_cursor())
