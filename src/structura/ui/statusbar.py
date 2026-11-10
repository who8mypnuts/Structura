"""Status bar segments (docs/14 §6): cursor, encoding, dialect, object count, build time, device, activity.

``track`` follows the current editor tab: its cursor position, file encoding / line endings and dialect."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QLabel, QProgressBar, QStatusBar, QWidget

if TYPE_CHECKING:
    from .documents import DocumentTabs, EditorTab


class StatusBar(QStatusBar):
    SEGMENTS = ("vim", "cursor", "encoding", "dialect", "objects", "build", "render", "device")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.labels = {name: QLabel("") for name in self.SEGMENTS}
        self.labels["cursor"].setMinimumWidth(110)  # permanent widgets keep their first size hint otherwise
        self.labels["encoding"].setToolTip("File encoding and line endings (kept when saving)")
        self.busy = QProgressBar()
        self.busy.setRange(0, 0)  # indeterminate spinner while a build runs
        self.busy.setMaximumWidth(90)
        self.busy.hide()
        for name in self.SEGMENTS:
            self.addPermanentWidget(self.labels[name])
        self.addPermanentWidget(self.busy)
        self.set("dialect", "EisenScript v1")
        self._tabs: DocumentTabs | None = None

    def set(self, segment: str, text: str) -> None:
        self.labels[segment].setText(text)

    def set_busy(self, busy: bool) -> None:
        self.busy.setVisible(busy)

    # -- the current tab -----------------------------------------------------------------------------------
    def track(self, tabs: DocumentTabs) -> None:
        self._tabs = tabs
        tabs.tab_added.connect(self._watch)
        tabs.current_tab_changed.connect(self.show_tab)

    def _watch(self, tab: EditorTab) -> None:
        tab.editor.cursor_moved.connect(partial(self._cursor, tab))
        tab.editor.vim.mode_changed.connect(partial(self._vim, tab))
        tab.saved.connect(partial(self._saved, tab))

    def _is_current(self, tab: EditorTab) -> bool:
        return self._tabs is not None and self._tabs.current() is tab

    def _cursor(self, tab: EditorTab, line: int, column: int) -> None:
        if self._is_current(tab):
            self.set("cursor", f"Ln {line}, Col {column}")

    def _vim(self, tab: EditorTab, _mode: str) -> None:
        if self._is_current(tab):
            self.set("vim", tab.editor.vim.label())

    def _saved(self, tab: EditorTab) -> None:
        if self._is_current(tab):
            self.show_tab(tab)

    def show_tab(self, tab: EditorTab | None) -> None:
        if tab is None:
            return
        cursor = tab.editor.textCursor()
        self.set("cursor", f"Ln {cursor.blockNumber() + 1}, Col {cursor.positionInBlock() + 1}")
        self.set("encoding", tab.file.label)
        self.set("dialect", tab.language_label)
        self.set("vim", tab.editor.vim.label())
