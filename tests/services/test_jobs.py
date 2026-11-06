"""The Job framework: outcomes, streaming, latest-wins, cancellation, thread placement (docs/04)."""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator

import pytest
from PySide6.QtCore import QObject, Slot
from pytestqt.qtbot import QtBot

from structura.services.jobs import ErrorInfo, FunctionJob, JobContext, JobRunner, Lane


class Recorder(QObject):
    def __init__(self) -> None:
        super().__init__()
        self.events: list[tuple[str, object]] = []
        self.threads: set[str] = set()

    def _note(self, kind: str, value: object) -> None:
        self.events.append((kind, value))
        self.threads.add(threading.current_thread().name)

    @Slot(object)
    def on_finished(self, v: object) -> None:
        self._note("finished", v)

    @Slot(object)
    def on_failed(self, v: object) -> None:
        self._note("failed", v)

    @Slot()
    def on_cancelled(self) -> None:
        self._note("cancelled", None)

    @Slot(object)
    def on_partial(self, v: object) -> None:
        self._note("partial", v)


@pytest.fixture
def runner() -> Iterator[JobRunner]:
    r = JobRunner()
    yield r
    r.shutdown()


def _watch(handle: object, rec: Recorder) -> None:
    handle.finished.connect(rec.on_finished)  # type: ignore[attr-defined]
    handle.failed.connect(rec.on_failed)  # type: ignore[attr-defined]
    handle.cancelled.connect(rec.on_cancelled)  # type: ignore[attr-defined]
    handle.partial.connect(rec.on_partial)  # type: ignore[attr-defined]


def test_result_and_partials_arrive_on_the_gui_thread(qtbot: QtBot, runner: JobRunner) -> None:
    rec = Recorder()
    worker_thread: list[str] = []

    def work(ctx: JobContext) -> int:
        worker_thread.append(threading.current_thread().name)
        for i in range(3):
            ctx.partial(i)
        return 42

    handle = runner.submit(FunctionJob("answer", Lane.BUILD, work))
    _watch(handle, rec)
    qtbot.waitUntil(lambda: handle.done, timeout=5000)
    qtbot.waitUntil(lambda: ("finished", 42) in rec.events, timeout=5000)
    assert [v for k, v in rec.events if k == "partial"] == [0, 1, 2]
    assert rec.threads == {threading.current_thread().name}  # slots ran on the GUI thread
    assert worker_thread != [threading.current_thread().name]


def test_exceptions_become_error_info(qtbot: QtBot, runner: JobRunner) -> None:
    rec = Recorder()

    def boom(ctx: JobContext) -> None:
        raise ValueError("bad value")

    handle = runner.submit(FunctionJob("boom", Lane.IO, boom))
    _watch(handle, rec)
    qtbot.waitUntil(lambda: bool(rec.events), timeout=5000)
    kind, info = rec.events[0]
    assert kind == "failed" and isinstance(info, ErrorInfo) and "bad value" in info.message


def test_latest_wins_cancels_the_previous_job_with_the_same_key(qtbot: QtBot, runner: JobRunner) -> None:
    first, second = Recorder(), Recorder()
    gate = threading.Event()

    def slow(ctx: JobContext) -> str:
        while not gate.is_set():
            ctx.check_cancelled()
            time.sleep(0.005)
        return "slow"

    h1 = runner.submit(FunctionJob("build", Lane.BUILD, slow, key="doc"))
    _watch(h1, first)
    qtbot.waitUntil(lambda: h1.state == "running", timeout=5000)
    h2 = runner.submit(FunctionJob("build", Lane.BUILD, lambda ctx: "fast", key="doc"))
    _watch(h2, second)
    qtbot.waitUntil(lambda: h1.done and h2.done, timeout=5000)
    gate.set()
    qtbot.waitUntil(lambda: bool(first.events) and bool(second.events), timeout=5000)
    assert first.events == [("cancelled", None)]
    assert second.events == [("finished", "fast")]
    qtbot.waitUntil(lambda: not runner.active(), timeout=5000)


def test_signals_connected_right_after_submit_are_never_missed(qtbot: QtBot, runner: JobRunner) -> None:
    recorders = []
    for i in range(50):  # instant jobs: without deferred dispatch some finish before connect() runs
        rec = Recorder()
        handle = runner.submit(FunctionJob(f"instant {i}", Lane.ANALYSIS, lambda ctx, i=i: i))
        _watch(handle, rec)
        recorders.append(rec)
    qtbot.waitUntil(lambda: all(r.events for r in recorders), timeout=5000)
    assert [r.events[0] for r in recorders] == [("finished", i) for i in range(50)]
