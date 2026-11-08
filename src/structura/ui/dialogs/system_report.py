"""Help ▸ System Report… (docs/14 §4.1 'Report Issue'): runs `structura doctor` in a separate process — the
GUI never waits — and shows what it finds (Qt platform, OpenGL, compute devices) with a Copy button, for
bug reports."""

from __future__ import annotations

from PySide6.QtCore import QProcess, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QPlainTextEdit, QVBoxLayout, QWidget

from ...services.script_process import cli_command
from ..fonts import use_code_font
from ..i18n import tr


class SystemReport(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("System Report"))
        self.resize(720, 520)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        use_code_font(self.text)
        self.text.setAccessibleName(tr("System report"))
        self.text.setPlaceholderText(tr("Collecting… (structura doctor)"))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        copy = buttons.addButton(tr("Copy"), QDialogButtonBox.ButtonRole.ActionRole)
        copy.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.text.toPlainText()))
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self.text, 1)
        layout.addWidget(buttons)
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._output)

    def start(self) -> None:
        program, arguments = cli_command("doctor")
        self.process.start(program, arguments)
        self.show()

    @Slot()
    def _output(self) -> None:
        chunk = bytes(self.process.readAllStandardOutput().data()).decode(errors="replace")
        self.text.insertPlainText(chunk)
