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


def _wait_for_exec(pid: int, marker: str) -> None:
    """Waits until a just-started child runs its own program (right after fork it still looks like its parent)."""
    import time  # noqa: PLC0415

    import psutil  # noqa: PLC0415

    deadline = time.monotonic() + 10.0
    while marker not in " ".join(psutil.Process(pid).cmdline()) and time.monotonic() < deadline:
        time.sleep(0.01)


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
    other = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)", "structura"])  # (its argv)
    try:
        _wait_for_exec(other.pid, "time.sleep")
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
    script.write_text("box // newest\n")  # a second save within the same second keeps the older backup
    back_up(script, folder, start + timedelta(seconds=KEEP + 2))
    assert backups_of(folder, script)[0].read_text() == f"box // {KEEP + 2}\n"


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


def test_a_failing_device_query_never_stops_a_render() -> None:
    from structura.compute.base import device_details  # noqa: PLC0415
    from structura.compute.cpu import CpuBackend  # noqa: PLC0415

    class Broken(CpuBackend):
        def details(self) -> dict[str, str]:
            """Fails like a lost driver."""
            raise RuntimeError("driver gone")

    assert "Numba" in device_details(CpuBackend())
    assert device_details(Broken()) == {"Details": "unavailable (RuntimeError: driver gone)"}


def test_a_reused_pid_of_another_program_still_means_a_crash(tmp_path: Path) -> None:
    other = subprocess.Popen(["sleep", "30"])  # alive, but not Structura: the crashed run's PID was reused
    try:
        _wait_for_exec(other.pid, "sleep")
        (tmp_path / "running.lock").write_text(str(other.pid))
        assert CrashGuard(tmp_path).start()
    finally:
        other.kill()
        other.wait()


def test_a_malformed_tab_does_not_lose_the_others() -> None:
    import json  # noqa: PLC0415

    from structura.services.session import FORMAT, SessionState  # noqa: PLC0415

    tabs = [{"path": None, "text": "box"}, {"folded": ["x"]}, {"text": 5}, "junk", {"text": "sphere"}]
    state = SessionState.from_json(json.dumps({"format": FORMAT, "tabs": tabs, "current": 9}))
    assert [t.text for t in state.tabs] == ["box", "sphere"] and state.current == 1
