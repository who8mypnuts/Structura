"""External programs started from the app (template 'runAfter' commands): non-blocking QProcess, output piped
to the Console, a toast when they finish (docs/15 §5.2)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QProcess, Slot

from .i18n import tr

if TYPE_CHECKING:
    from .app_window import MainWindow


class ProcessRunner(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        self.running: list[QProcess] = []

    def start(self, command: str, cwd: Path) -> QProcess:
        process = QProcess(self)
        process.setWorkingDirectory(str(cwd))
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(self._output)
        process.finished.connect(self._finished)
        process.errorOccurred.connect(self._error)
        self.running.append(process)
        self.w.console.info(f"$ {command}")
        process.startCommand(command)
        return process

    def _process(self) -> QProcess | None:
        sender = self.sender()
        return sender if isinstance(sender, QProcess) else None

    @Slot()
    def _output(self) -> None:
        process = self._process()
        if process is not None:
            text = bytes(process.readAllStandardOutput().data()).decode(errors="replace")
            for line in text.splitlines():
                self.w.console.info(line)

    @Slot(int, QProcess.ExitStatus)
    def _finished(self, code: int, _status: QProcess.ExitStatus) -> None:
        process = self._process()
        if process is None:
            return
        name = Path(process.program()).name
        self.w.toasts.show(tr("{name} finished (exit code {code})").format(name=name, code=code))
        self._forget(process)

    @Slot(QProcess.ProcessError)
    def _error(self, _error: QProcess.ProcessError) -> None:
        process = self._process()
        if process is not None and process.state() == QProcess.ProcessState.NotRunning:
            self.w.show_message(tr("Could not run {program}: {error}").format(program=process.program(),
                                                                             error=process.errorString()))  # fmt: skip
            self._forget(process)

    def _forget(self, process: QProcess) -> None:
        if process in self.running:
            self.running.remove(process)
        process.deleteLater()
