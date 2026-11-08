"""Run a '#javascript' script for the window (docs/16 §3): `structura run --ipc` in a QProcess, so no script
can freeze the GUI. The child's channel lines (services/scripting.py) become signals; questions are answered
on its stdin; Cancel kills it. Scenes it hands over are loaded and prepared for the viewport on the io lane."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QProcess, Signal, Slot

from ..core.scene.ir_io import load_scene
from ..preview.instances import preview_scene
from .jobs import FunctionJob, JobContext, JobRunner, Lane
from .scripting import PREFIX


def cli_command(*arguments: str) -> tuple[str, list[str]]:
    """The `structura` command line: the bundled executable beside a frozen app, else this Python's module."""
    if getattr(sys, "frozen", False):
        name = "structura.exe" if sys.platform == "win32" else "structura"
        return str(Path(sys.executable).with_name(name)), list(arguments)
    return sys.executable, ["-m", "structura.cli.main", *arguments]


class ScriptProcess(QObject):
    info = Signal(str)  # Debug.Info, "raytraced f.png", anything else the script prints
    message = Signal(str)  # Debug.Message (shown without blocking)
    progress = Signal(object, object)  # caption | None, fraction | None (None, None: hide)
    scene = Signal(object, object)  # SceneIR, PreviewScene: Builder.build and World
    click = Signal()  # Debug.waitForMouseButton: answer(True) continues, answer(False) stops
    confirm = Signal(str)  # Builder.execute: answer whether this command may run
    finished = Signal(int, str)  # exit code, the last error line ('' when none)

    def __init__(self, runner: JobRunner, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.runner = runner
        self.process: QProcess | None = None
        self.error = ""
        self._buffer = b""

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.state() != QProcess.ProcessState.NotRunning

    def start(self, text: str, script_dir: Path, device: str) -> None:
        self.cancel()
        script = Path(tempfile.mkstemp(prefix="structura-", suffix=".es")[1])
        script.write_text(text, encoding="utf-8")
        program, arguments = cli_command("run", str(script), "--ipc", "--dir", str(script_dir), "--device", device)
        self.process, self.error, self._buffer = QProcess(self), "", b""
        self.process.readyReadStandardOutput.connect(self._read)
        self.process.readyReadStandardError.connect(self._read_errors)
        self.process.finished.connect(self._finished)
        self.process.start(program, arguments)

    def cancel(self) -> None:
        if self.running:
            assert self.process is not None
            self.process.kill()

    def answer(self, yes: bool) -> None:
        if self.running:
            assert self.process is not None
            self.process.write(b"1\n" if yes else b"0\n")

    @Slot()
    def _read(self) -> None:
        assert self.process is not None
        self._buffer += bytes(self.process.readAllStandardOutput().data())
        *lines, self._buffer = self._buffer.split(b"\n")
        for raw in lines:
            line = raw.decode(errors="replace").rstrip("\r")
            if line.startswith(PREFIX):
                self._dispatch(json.loads(line[len(PREFIX) :]))
            elif line.strip():
                self.info.emit(line)

    @Slot()
    def _read_errors(self) -> None:
        assert self.process is not None
        for line in bytes(self.process.readAllStandardError().data()).decode(errors="replace").splitlines():
            if line.strip():
                self.error = line.strip()
                self.info.emit(line)

    def _dispatch(self, message: dict[str, Any]) -> None:
        if "info" in message:
            self.info.emit(str(message["info"]))
        elif "message" in message:
            self.message.emit(str(message["message"]))
        elif "progress" in message:
            caption, fraction = message["progress"]
            self.progress.emit(caption, fraction)
        elif "scene" in message:
            self._load(Path(str(message["scene"])))
        elif isinstance(message.get("ask"), dict):
            question = message["ask"]
            if question.get("kind") == "click":
                self.click.emit()
            else:
                self.confirm.emit(str(question.get("command", "")))

    def _load(self, path: Path) -> None:
        def run(ctx: JobContext) -> tuple[object, object]:
            scene = load_scene(path)
            return scene, preview_scene(scene)

        job = FunctionJob("script scene", Lane.IO, run, key="script-scene")
        self.runner.submit(job).finished.connect(self._loaded)

    @Slot(object)
    def _loaded(self, result: object) -> None:
        if isinstance(result, tuple):
            self.scene.emit(*result)

    @Slot(int, QProcess.ExitStatus)
    def _finished(self, code: int, status: QProcess.ExitStatus) -> None:
        crashed = status == QProcess.ExitStatus.CrashExit
        self.finished.emit(-1 if crashed else code, self.error)
