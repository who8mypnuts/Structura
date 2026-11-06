"""Run Structure Synth '#javascript' scripts from the window (docs/16 §3): Build ▸ Run JavaScript runs the
current script as a background job; each written file is reported in the console; Cancel stops it."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Slot

from ..services.jobs import ErrorInfo
from ..services.scripting import ScriptingService

if TYPE_CHECKING:
    from .app_window import MainWindow


class ScriptActions(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        self.service = ScriptingService(window.runner)
        self.service.message.connect(self._message)
        self.service.finished.connect(self._finished)
        self.service.failed.connect(self._failed)

    def can_run(self) -> bool:
        tab = self.w.tabs.current()
        return tab is not None and tab.is_javascript

    def run(self) -> None:
        tab = self.w.tabs.current()
        if tab is None or not tab.is_javascript:
            self.w.show_message("Run JavaScript needs a '#javascript' script")
            return
        folder = tab.path.parent if tab.path else Path.home()
        self.w.show_message(f"Running {tab.display_name} (files are written to {folder})")
        self.w.status.set_busy(True)
        self.service.run(tab.doc_id, tab.text(), folder, self.w.render_view.device.currentText())

    def cancel(self) -> None:
        tab = self.w.tabs.current()
        if tab is not None:
            self.service.cancel(tab.doc_id)

    @Slot(str, str)
    def _message(self, _doc: str, text: str) -> None:
        self.w.console.info(text)

    @Slot(str, int)
    def _finished(self, _doc: str, written: int) -> None:
        self.w.status.set_busy(False)
        self.w.show_message(f"JavaScript finished: {written} file{'s' if written != 1 else ''} written")

    @Slot(str, object)
    def _failed(self, _doc: str, info: object) -> None:
        self.w.status.set_busy(False)
        message = info.message if isinstance(info, ErrorInfo) else str(info)
        self.w.show_message(f"JavaScript failed: {message}")
