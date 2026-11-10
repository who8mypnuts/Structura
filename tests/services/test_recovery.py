"""Crash detection, backups on save and the crash diagnostics (PLAN Q6)."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from datetime import datetime, timedelta
from pathlib import Path

from structura.app.diagnostics import Diagnostics
from structura.services.backups import KEEP, back_up, backups_of
from structura.services.session import CrashGuard


def _dead_pid() -> int:
    process = subprocess.Popen([sys.executable, "-c", "pass"])
    process.wait()
    return process.pid


def test_a_lock_left_by_a_dead_process_means_a_crash(tmp_path: Path) -> None:
    guard = CrashGuard(tmp_path)
    assert not guard.start()  # a first start: nothing was left behind
    guard.lock.write_text(str(_dead_pid()))  # the process died without stop()
    again = CrashGuard(tmp_path)
    assert again.start() and again.lock.read_text() == str(os.getpid())
    again.recovery.write_text("{}")
    again.stop()
    assert not again.lock.exists() and not again.recovery.exists()
    assert not CrashGuard(tmp_path).start()  # a clean exit is no crash


def test_a_second_running_instance_keeps_its_own_files(tmp_path: Path) -> None:
    other = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        (tmp_path / "running.lock").write_text(str(other.pid))
        guard = CrashGuard(tmp_path)
        assert not guard.start()  # the other instance is alive: no crash
        assert guard.lock.name == f"running-{os.getpid()}.lock" and guard.recovery.name.startswith("recovery-")
    finally:
        other.kill()
        other.wait()


def test_backups_keep_the_newest_copies(tmp_path: Path) -> None:
    script, folder = tmp_path / "tree.es", tmp_path / "backups"
    assert back_up(script, folder) is None  # nothing on disk yet
    start = datetime(2026, 1, 1, 12, 0, 0)
    for n in range(KEEP + 3):
        script.write_text(f"box // {n}\n")
        back_up(script, folder, start + timedelta(seconds=n))
    kept = backups_of(folder, script)
    assert len(kept) == KEEP and kept[0].read_text() == f"box // {KEEP + 2}\n"


def test_unhandled_exceptions_are_logged_and_reported(tmp_path: Path) -> None:
    diagnostics = Diagnostics(tmp_path / "logs")
    try:
        diagnostics.install()
        seen: list[tuple[str, str]] = []
        diagnostics.on_error = lambda summary, details: seen.append((summary, details))
        try:
            raise ValueError("boom")
        except ValueError as exc:
            sys.excepthook(type(exc), exc, exc.__traceback__)
        worker = threading.Thread(target=lambda: 1 / 0)
        worker.start()
        worker.join()
        assert [s for s, _ in seen] == ["ValueError: boom", "ZeroDivisionError: division by zero"]
        assert "Traceback" in seen[0][1]
        assert "ValueError: boom" in (tmp_path / "logs" / "structura.log").read_text(encoding="utf-8")
    finally:
        diagnostics.close()
