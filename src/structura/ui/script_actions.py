"""Run Structure Synth '#javascript' scripts from the window (docs/16 §3): Build ▸ Run JavaScript runs the
current script in a separate process (services/script_process.py); what it reports goes to the console, the
scenes it builds to the viewport; Cancel stops it."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QFileDialog

from ..services.script_process import ScriptProcess, cli_command
from .i18n import tr
from .script_requests import ScriptUi

if TYPE_CHECKING:
    from .app_window import MainWindow


class ScriptActions(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        self.process = ScriptProcess(window.runner, self)
        self.process.finished.connect(self._finished)
        self.ui = ScriptUi(window, self.process)
        self.written = 0

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
        self.process.start(tab.text(), folder, self.w.render_view.device.currentText())

    def cancel(self) -> None:
        self.process.cancel()

    def run_python(self, path: Path | None = None) -> None:
        """Build ▸ Run Python Script…: a script using the Python API, run by `structura run` in its own process;
        its output goes to the Console."""
        if path is None:
            chosen, _ = QFileDialog.getOpenFileName(self.w, tr("Run Python Script"), str(Path.home()),
                                                    tr("Python scripts (*.py)"))  # fmt: skip
            if not chosen:
                return
            path = Path(chosen)
        program, arguments = cli_command("run", str(path))
        self.w.processes.start_program(program, arguments, path.parent)

    @Slot(int, str)
    def _finished(self, code: int, error: str) -> None:
        self.w.status.set_busy(False)
        if code == 0:
            self.w.show_message("JavaScript finished")
        elif code == -1:
            self.w.show_message("JavaScript stopped")
        else:
            self.w.show_message(f"JavaScript failed: {error}")
