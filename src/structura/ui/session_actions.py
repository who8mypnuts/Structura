"""Session restore, hot exit and crash recovery for the main window (docs/12 §2.1, docs/07 §8).

- Start-up: if the last run crashed (its running lock survived, services/session.CrashGuard), offer to restore
  its recovery snapshot; otherwise reopen the previous session. Files given on the command line open as well.
- While editing: a recovery snapshot of every tab is written EDIT_DELAY_MS after the last edit, and every
  ``general/autosave_seconds``; after an internal error it is written at once.
- Quit: with hot exit on (the default) the session, unsaved text included, is saved and nothing is asked;
  otherwise each modified tab asks as before. The window geometry and dock layout are kept too.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QByteArray, QObject, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox

from ..core.animation.timeline import from_dict as timeline_from
from ..core.animation.timeline import to_dict as timeline_dict
from ..core.params import ParamSpec, ParamType
from ..core.project.model import camera_from_dict, camera_to_dict
from ..core.scene.camera import Camera
from ..core.text_file import TextFile
from ..services.session import CrashGuard, SessionState, SessionStore, TabState
from .dock_layout import LAYOUT_VERSION
from .documents import EditorTab
from .i18n import tr

if TYPE_CHECKING:
    from .app_window import MainWindow

SPECS = (
    ParamSpec("general/restore_session", ParamType.BOOL, True, "Reopen the previous session's tabs"),
    ParamSpec("general/hot_exit", ParamType.BOOL, True, "Keep unsaved edits between sessions (no prompt on quit)"),
    ParamSpec("general/autosave_seconds", ParamType.INT, 60, "Recovery snapshot interval (s)", range=(10, 600)),
)
EDIT_DELAY_MS = 5000  # a recovery snapshot this long after the last edit


class SessionActions(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        base = window.settings.directory()
        self.session = SessionStore(base / "session.json")
        self.guard = CrashGuard(base)
        self.recovery = SessionStore(self.guard.recovery)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.autosave)
        self.edit_timer = QTimer(self)
        self.edit_timer.setSingleShot(True)
        self.edit_timer.setInterval(EDIT_DELAY_MS)
        self.edit_timer.timeout.connect(self.autosave)
        window.tabs.tab_edited.connect(lambda _tab: self.edit_timer.start())
        self.split_restored = False

    def _setting(self, key: str) -> object:
        spec = next(s for s in SPECS if s.key == key)
        return self.w.settings.value(key, spec.default)

    # -- snapshots -----------------------------------------------------------------------------------------
    def snapshot(self) -> SessionState:
        current = self.w.tabs.current()
        states = (
            _tab_state(t, self.w.viewport.camera() if t is current else t.initial_camera) for t in self.w.tabs.tabs()
        )
        return SessionState(tuple(states), max(0, self.w.tabs.currentIndex()))

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
        _apply_extras(tab, state)
        tab.seed = state.seed
        tab.editor.go_to(min(state.cursor, len(tab.text())))
        tab.editor.folding.refresh()
        for line in state.folded:
            tab.editor.folding.toggle(line)
        return tab

    def autosave(self) -> None:
        """Write the recovery snapshot (every tab, saved or not): what a crash would otherwise lose."""
        state = self.snapshot()
        if state.empty:
            self.recovery.clear()
        else:
            self.recovery.save(state)

    # -- start-up and quit -----------------------------------------------------------------------------------
    def startup(self, files: list[Path]) -> None:
        crashed = self.guard.start()
        self.recovery = SessionStore(self.guard.recovery)  # another instance keeps its own file
        pending = self.recovery.load() if crashed else None
        if pending is not None and not pending.empty and self._offer_recovery(pending):
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
        count, unsaved = len(pending.tabs), pending.unsaved_count
        question = (f"Structura did not shut down cleanly. Restore the {count} script{'s' if count != 1 else ''} "
                    f"that {'were' if count != 1 else 'was'} open ({unsaved} with unsaved changes)?")  # fmt: skip
        answer = QMessageBox.question(self.w, "Recover unsaved scripts", question)
        if answer != QMessageBox.StandardButton.Yes:
            SessionStore(self.recovery.path.with_name("recovery-declined.json")).save(pending)  # never lost
            return False
        return True

    def restore_declined(self) -> None:
        """File ▸ Recover ▸ Restore Declined Recovery: the snapshot kept when recovery was declined."""
        declined = SessionStore(self.recovery.path.with_name("recovery-declined.json"))
        state = declined.load()
        if state is None or state.empty:
            self.w.show_message(tr("There is no declined recovery snapshot."))
            return
        count = self.restore(state)
        self.w.show_message(tr("Restored {count} script(s) from the declined recovery").format(count=count))

    def open_backups(self) -> None:
        """File ▸ Recover ▸ Open Backups Folder."""
        folder = self.w.docs.backups
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

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
        self.guard.stop()
        self.timer.stop()
        self.edit_timer.stop()
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
        restored = bool(self.w.restoreGeometry(geometry) and self.w.panels.restore(state))
        QTimer.singleShot(0, self.w.fit_to_screen)  # geometry saved while a panel had grown the window
        return restored


def _apply_extras(tab: EditorTab, state: TabState) -> None:
    """The parameters, render overrides, camera, saved views and timeline a snapshot kept for the tab."""
    tab.params = {str(k): float(v) for k, v in state.params.items()}
    tab.render_overrides = dict(state.render_overrides)
    tab.initial_camera = camera_from_dict(state.camera) or tab.initial_camera
    views = {name: camera_from_dict(data) for name, data in state.bookmarks.items()}
    tab.bookmarks = {name: camera for name, camera in views.items() if camera is not None}
    if state.timeline:
        tab.timeline = timeline_from(state.timeline)


def _tab_state(tab: EditorTab, camera: Camera | None) -> TabState:
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
        params=dict(tab.params),
        render_overrides=dict(tab.render_overrides),
        camera=camera_to_dict(camera),
        bookmarks={name: camera_to_dict(view) for name, view in tab.bookmarks.items()},
        timeline=timeline_dict(tab.timeline) if tab.timeline.tracks else None,
    )
