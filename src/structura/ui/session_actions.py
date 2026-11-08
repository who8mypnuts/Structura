"""Session restore, hot exit and crash recovery for the main window (docs/12 §2.1, docs/07 §8).

- Start-up: if a recovery snapshot survived (the last run crashed), offer to restore it; otherwise reopen the
  previous session. Files given on the command line open as well.
- While editing: a recovery snapshot is written every ``general/autosave_seconds`` when anything is unsaved.
- Quit: with hot exit on (the default) the session, unsaved text included, is saved and nothing is asked;
  otherwise each modified tab asks as before. The window geometry and dock layout are kept too.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QByteArray, QObject, QTimer
from PySide6.QtWidgets import QMessageBox

from ..core.params import ParamSpec, ParamType
from ..core.text_file import TextFile
from ..services.session import SessionState, SessionStore, TabState
from .dock_layout import LAYOUT_VERSION
from .documents import EditorTab

if TYPE_CHECKING:
    from .app_window import MainWindow

SPECS = (
    ParamSpec("general/restore_session", ParamType.BOOL, True, "Reopen the previous session's tabs"),
    ParamSpec("general/hot_exit", ParamType.BOOL, True, "Keep unsaved edits between sessions (no prompt on quit)"),
    ParamSpec("general/autosave_seconds", ParamType.INT, 60, "Recovery snapshot interval (s)", range=(10, 600)),
)


class SessionActions(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        base = window.settings.directory()
        self.session = SessionStore(base / "session.json")
        self.recovery = SessionStore(base / "recovery.json")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.autosave)
        self.split_restored = False

    def _setting(self, key: str) -> object:
        spec = next(s for s in SPECS if s.key == key)
        return self.w.settings.value(key, spec.default)

    # -- snapshots -----------------------------------------------------------------------------------------
    def snapshot(self) -> SessionState:
        return SessionState(tuple(_tab_state(t) for t in self.w.tabs.tabs()), max(0, self.w.tabs.currentIndex()))

    def restore(self, state: SessionState) -> int:
        restored = [tab for t in state.tabs if (tab := self._restore_tab(t)) is not None]
        if restored:
            self.w.tabs.setCurrentIndex(min(state.current, self.w.tabs.count() - 1))
        return len(restored)

    def _restore_tab(self, state: TabState) -> EditorTab | None:
        path = Path(state.path) if state.path else None
        if state.project and state.text is None and Path(state.project).exists():
            return self.w.projects.open(Path(state.project))
        if state.text is None:
            if path is None or not path.exists():
                return None
            tab = self.w.tabs.open_file(path)
        else:
            file = TextFile(state.text, state.encoding, state.newline)
            tab = self.w.tabs.new_document(state.text, path, file)
            tab.editor.document().setModified(True)  # still unsaved
        if state.project:
            tab.project_path = Path(state.project)
            tab.retitle()
        tab.seed = state.seed
        tab.editor.go_to(min(state.cursor, len(tab.text())))
        tab.editor.folding.refresh()
        for line in state.folded:
            tab.editor.folding.toggle(line)
        return tab

    def autosave(self) -> None:
        state = self.snapshot()
        if state.unsaved_count:
            self.recovery.save(state)
        else:
            self.recovery.clear()

    # -- start-up and quit -----------------------------------------------------------------------------------
    def startup(self, files: list[Path]) -> None:
        pending = self.recovery.load()
        if pending is not None and pending.unsaved_count and self._offer_recovery(pending):
            self.restore(pending)
        elif not files and self._setting("general/restore_session") and (state := self.session.load()):
            self.restore(state)
        self.recovery.clear()
        for path in files:
            self.w.docs.open_file(path)
        if not self.w.tabs.count():
            self.w.docs.new_script()
        self.timer.start(int(str(self._setting("general/autosave_seconds"))) * 1000)

    def _offer_recovery(self, pending: SessionState) -> bool:
        count = pending.unsaved_count
        question = (f"Structura did not shut down cleanly. Restore {count} unsaved "
                    f"script{'s' if count != 1 else ''}?")  # fmt: skip
        answer = QMessageBox.question(self.w, "Recover unsaved scripts", question)
        if answer != QMessageBox.StandardButton.Yes:
            SessionStore(self.recovery.path.with_name("recovery-declined.json")).save(pending)  # never lost
            return False
        return True

    def shutdown(self) -> bool:
        """Called when the window closes; False cancels the close."""
        state = self.snapshot()
        if not self._setting("general/hot_exit"):
            saved_only = tuple(replace(t, text=None) for t in state.tabs if t.path is not None)
            state = replace(state, tabs=saved_only, current=0)
            for index in reversed(range(self.w.tabs.count())):
                if not self.w.tabs.close_tab(index):
                    return False
        self.session.save(state)
        self.recovery.clear()
        self.timer.stop()
        self.w.settings.set_value("window/geometry", self.w.saveGeometry())
        self.w.settings.set_value("window/state", self.w.saveState(LAYOUT_VERSION))
        self.w.settings.set_value("window/split", self.w.split.saveState())
        return True

    def restore_layout(self) -> bool:
        """Restore the saved window geometry and dock layout; False when there is none."""
        geometry, state = self.w.settings.value("window/geometry"), self.w.settings.value("window/state")
        if not isinstance(geometry, QByteArray) or not isinstance(state, QByteArray):
            return False
        split = self.w.settings.value("window/split")
        self.split_restored = isinstance(split, QByteArray) and self.w.split.restoreState(split)
        return bool(self.w.restoreGeometry(geometry) and self.w.panels.restore(state))


def _tab_state(tab: EditorTab) -> TabState:
    unsaved = tab.modified or tab.path is None
    return TabState(
        path=str(tab.path) if tab.path else None,
        text=tab.text() if unsaved else None,
        cursor=tab.editor.textCursor().position(),
        seed=tab.seed,
        folded=tuple(sorted(tab.editor.folding.folded_lines())),
        encoding=tab.file.encoding,
        newline=tab.file.newline,
        project=str(tab.project_path) if tab.project_path else None,
    )
