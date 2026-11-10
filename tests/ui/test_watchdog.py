"""The UI-stall watchdog (docs/18 §7) notices a slot that blocks the event loop."""

from __future__ import annotations

import time

from PySide6.QtCore import QTimer
from pytestqt.qtbot import QtBot

from structura.ui.watchdog import StallWatchdog


def test_a_blocking_slot_is_a_stall_with_its_stack(qtbot: QtBot) -> None:
    watchdog = StallWatchdog(budget_ms=30)
    QTimer.singleShot(0, lambda: time.sleep(0.12))  # a slot that blocks for 120 ms
    qtbot.wait(200)
    stalls = watchdog.stop()
    assert stalls and max(s.milliseconds for s in stalls) >= 100
    assert any("test_watchdog" in s.stack for s in stalls)  # the sampled stack shows the culprit


def test_work_outside_the_event_loop_is_not_a_stall(qtbot: QtBot) -> None:
    watchdog = StallWatchdog(budget_ms=30)
    qtbot.wait(20)
    time.sleep(0.1)  # the test itself, not an event handler
    qtbot.wait(20)
    stalls = watchdog.stop()
    assert stalls and not any("pytestqt" in s.stack for s in stalls)  # a gap, but not inside the event loop


def test_the_sampler_thread_never_owns_the_watchdog(qtbot: QtBot) -> None:
    """A thread holding the last reference to a QObject would destroy it off the GUI thread, which deadlocks
    PySide against the GUI thread (seen as a UI test suite that hung at random)."""
    import gc  # noqa: PLC0415
    import weakref  # noqa: PLC0415

    watchdog = StallWatchdog(budget_ms=30)
    qtbot.wait(20)
    watchdog.stop()
    assert not watchdog._sampler.is_alive()  # stop() waits for it
    gone = weakref.ref(watchdog)
    del watchdog
    gc.collect()
    assert gone() is None  # destroyed here, on the GUI thread


def test_a_thread_stack_reads_like_traceback_oldest_call_first() -> None:
    """The sampler reads stacks through faulthandler (no frame objects change hands between threads, see
    `_sample`) and presents them as `traceback.format_stack` does, which the UI fixture parses."""
    import tempfile  # noqa: PLC0415
    import threading  # noqa: PLC0415

    from structura.ui.watchdog import _thread_stack  # noqa: PLC0415

    def inner() -> str:
        """Returns this thread's stack, sampled one call deeper than the test."""
        with tempfile.TemporaryFile() as dump:
            return _thread_stack(dump.fileno(), threading.get_ident())

    stack = inner()
    assert stack.index("in test_a_thread_stack_reads_like_traceback") < stack.index("in inner")
    assert f'File "{__file__}", line ' in stack
    with tempfile.TemporaryFile() as dump:
        assert _thread_stack(dump.fileno(), 0) == ""  # no such thread
