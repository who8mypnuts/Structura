"""Find in Files in the window (docs/12 §2.1): the Search dock searches the open tabs (their unsaved text)
and the scripts in the current file's folder; choosing a result opens it at the match."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Qt, Slot
from PySide6.QtWidgets import QDockWidget

from ..core.text_file import read_script
from ..core.text_search import script_files
from .i18n import tr
from .panels.search import SearchPanel

if TYPE_CHECKING:
    from .app_window import MainWindow

TAB = "tab:"


class SearchActions(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        self.panel = SearchPanel()
        self.dock = QDockWidget(tr("Search", "Panels"), window)
        self.dock.setObjectName("dock-search")
        self.dock.setWidget(self.panel)
        window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dock)
        window.tabifyDockWidget(window.docks["Problems"], self.dock)
        window.docks["Problems"].raise_()  # tabifying made Search the visible tab; Problems comes first
        window.docks["Search"] = self.dock
        self.panel.texts_wanted.connect(self.run)
        self.panel.open_match.connect(self.open_match)

    def show(self) -> None:
        self.dock.show()
        self.dock.raise_()
        self.panel.focus_query()

    def sources(self) -> tuple[dict[str, str], dict[str, str]]:
        """(source → text, source → label): open tabs first, then files of the current folder not open."""
        texts, labels, open_paths = {}, {}, set()
        for tab in self.w.tabs.tabs():
            texts[TAB + tab.doc_id], labels[TAB + tab.doc_id] = tab.text(), tab.display_name
            if tab.path is not None:
                open_paths.add(tab.path.resolve())
        current = self.w.tabs.current()
        if current is not None and current.path is not None:
            for path in script_files(current.path.parent):
                if path.resolve() not in open_paths:
                    texts[str(path)], labels[str(path)] = read_script(path), str(path.relative_to(current.path.parent))
        return texts, labels

    @Slot()
    def run(self) -> None:
        self.panel.search_in(*self.sources())

    @Slot(str, int)
    def open_match(self, source: str, offset: int) -> None:
        if source.startswith(TAB):
            tab = next((t for t in self.w.tabs.tabs() if t.doc_id == source[len(TAB) :]), None)
            if tab is not None:
                self.w.tabs.setCurrentWidget(tab)
        else:
            tab = self.w.docs.open_file(Path(source))
        if tab is not None:
            tab.editor.go_to(offset)
