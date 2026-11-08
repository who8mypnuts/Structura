"""Sidebar: the left dock's panels (Examples, Outline, Parameters, Variations, Render Settings), as pages
of one tab widget instead of individually tabified docks (docs/14 §2).

Two reasons, not one:

- **Readable tabs.** Five panels tabified the native way have to share the dock's width; Qt shrinks and
  elides every label ("Render Set…", "Vari…") long before the dock is actually narrow. Scroll buttons
  instead of eliding keep every label whole; the overflow, if any, is one click away instead of unreadable.
- **A Qt layout bug.** Tabifying *two* separate dock areas at once (this one and the bottom panel group)
  leaves a second, stale tab bar drawn over the window on Qt 6.12 (reproduced back to Qt 6.8, where the same
  spare bar exists but stays hidden and empty — so this is a Qt regression, not a usage error). Only one
  area in the window may use native dock tabifying; this is the one that does not.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QTabWidget, QToolButton, QWidget

from .i18n import tr

# The native arrow glyph a QToolButton would normally draw (QStyle.PE_IndicatorArrowLeft/Right) does not
# survive the application stylesheet (docs/13 §5 gives every QToolButton a background and a border, which
# switches Qt to a styled-panel paint path that ignores the arrow). A plain text arrow always shows.
SCROLL_GLYPHS = {"ScrollLeftButton": "\u2039", "ScrollRightButton": "\u203a"}


class Sidebar(QTabWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setDocumentMode(True)
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setElideMode(Qt.TextElideMode.ElideNone)
        self.setUsesScrollButtons(True)
        self.tabBar().setExpanding(False)
        self.setAccessibleName(tr("Sidebar"))

    def add_panel(self, title: str, widget: QWidget) -> None:
        widget.setAccessibleName(title)
        index = self.addTab(widget, title)
        self.setTabToolTip(index, title)
        self._glyph_scroll_buttons()

    def _glyph_scroll_buttons(self) -> None:
        """Qt creates the tab bar's scroll buttons lazily, the first time the tabs overflow its width."""
        for button in self.tabBar().findChildren(QToolButton):
            if glyph := SCROLL_GLYPHS.get(button.objectName()):
                button.setText(glyph)
                button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)  # default: icon-only, no icon

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._glyph_scroll_buttons()
