"""Internal errors in the window (PLAN Q6): an exception nobody handled (app/diagnostics.py) writes the recovery
snapshot at once and shows a banner — "Structura hit an internal error" — with Details (the traceback and where
the logs are) and Copy Report (traceback and system report, for a bug report). The app keeps running; the
user's work is in the recovery snapshot either way."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Slot, qVersion
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QMessageBox

from ..render.report.system_sections import system_section
from .i18n import tr

if TYPE_CHECKING:
    from pathlib import Path

    from .app_window import MainWindow

KEY = "internal-error"


class ErrorReporter(QObject):
    reported = Signal(str, str)  # summary, traceback — emitted from any thread, handled on the GUI thread

    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        self.log_dir: Path | None = None
        self.last = ("", "")
        self.reported.connect(self._show)

    def report(self, summary: str, details: str) -> None:
        """Thread-safe entry point for the diagnostics hooks."""
        self.reported.emit(summary, details)

    @Slot(str, str)
    def _show(self, summary: str, details: str) -> None:
        self.last = (summary, details)
        self.w.session.autosave()  # the work is safe whatever happens next (the log line reaches the Console)
        text = tr("Structura hit an internal error ({summary}). Your scripts are saved in the recovery snapshot; "
                  "you can keep working.").format(summary=summary)  # fmt: skip
        actions = ((tr("Details"), self.details), (tr("Copy Report"), self.copy_report))
        self.w.banner.show_message(KEY, text, actions)

    def report_text(self) -> str:
        summary, details = self.last
        where = f"\nLogs: {self.log_dir}" if self.log_dir else ""
        system = "\n".join(f"{r.label}: {r.text}" for r in system_section({"Qt": qVersion()}).rows)
        return f"{summary}\n\n{details}{where}\n\n{system}"

    def details(self) -> None:
        box = QMessageBox(QMessageBox.Icon.Warning, tr("Internal Error"), self.last[0], parent=self.w)
        box.setDetailedText(self.report_text())
        box.exec()

    def copy_report(self) -> None:
        QGuiApplication.clipboard().setText(self.report_text())
        self.w.show_message(tr("The error report is on the clipboard"))
