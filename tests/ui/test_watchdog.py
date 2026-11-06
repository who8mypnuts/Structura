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
