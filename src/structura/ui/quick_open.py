"""Quick Open (Ctrl+P, docs/14 §4.2): open tabs, recent files and the examples by fuzzy name; '@name' jumps
to a rule of the current script and ':N' to a line."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..services.recent import RecentFiles
from .panels.examples import example_files
from .picker import Entry, PickerPopup, ranked

if TYPE_CHECKING:
    from .app_window import MainWindow


class QuickOpen(PickerPopup):
    placeholder = "Open a file · @ rule in this script · : line number"

    def __init__(self, window: MainWindow) -> None:
        self.w = window
        super().__init__(window)

    def entries(self, query: str) -> list[Entry]:
        if query.startswith("@"):
            return ranked(query[1:], self._rules())
        if query.startswith(":"):
            return self._line(query[1:])
        return ranked(query, self._files())

    def _files(self) -> list[Entry]:
        seen: set[Path] = set()
        entries: list[Entry] = []
        for tab in self.w.tabs.tabs():
            entries.append((tab.title, "open", ("tab", tab.doc_id)))
            if tab.path is not None:
                seen.add(tab.path.resolve())
        examples = [path for _group, path in example_files()]
        for group, paths in (("recent", RecentFiles(self.w.settings).paths()), ("example", examples)):
            for path in paths:
                if path.resolve() not in seen:
                    seen.add(path.resolve())
                    kind = "example" if group == "example" else "file"
                    entries.append((path.name, f"{group} · {path.parent.name}", (kind, str(path))))
        return entries

    def _rules(self) -> list[Entry]:
        tab = self.w.tabs.current()
        analysis = tab.analysis if tab is not None else None
        if tab is None or analysis is None:
            return []
        document = tab.editor.document()
        return [(f"rule {r.name}", f"line {document.findBlock(r.span.start).blockNumber() + 1}", ("at", r.span.start))
                for r in analysis.rules]  # fmt: skip

    def _line(self, text: str) -> list[Entry]:
        tab = self.w.tabs.current()
        if tab is None or not text.strip().isdigit():
            return []
        line = max(1, min(int(text), tab.editor.blockCount()))
        return [(f"Go to line {line}", "", ("at", tab.editor.document().findBlockByNumber(line - 1).position()))]

    def activate(self, payload: Any) -> None:
        kind, value = payload
        if kind == "tab":
            tab = next((t for t in self.w.tabs.tabs() if t.doc_id == value), None)
            if tab is not None:
                self.w.tabs.setCurrentWidget(tab)
        elif kind == "file":
            self.w.docs.open_file(Path(value))
        elif kind == "example":
            self.w.docs.open_example(Path(value))
        elif kind == "at" and (tab := self.w.tabs.current()) is not None:
            tab.editor.go_to(int(value))
