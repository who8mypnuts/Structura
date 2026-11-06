"""UI-stall watchdog (docs/04 §8, docs/18 §7, goal G9): a heartbeat timer on the GUI thread and a sampling
thread. A gap between two beats longer than the budget is a stall; while it is still going on, the sampler
captures the GUI thread's stack, which names the code that blocked the event loop.

In the app (STRUCTURA_WATCHDOG=50) any gap is a stall. Under test, code the test runs itself outside the event
loop also stops the heartbeat; the UI test fixture therefore only counts stalls whose stack shows the event
loop (pytest-qt's wait functions) running.
"""

from __future__ import annotations

import sys
import threading
import time
import traceback
from dataclasses import dataclass

from PySide6.QtCore import QObject, QTimer, Slot

BUDGET_MS = 50.0
BEAT_MS = 10
SAMPLE_S = 0.005


@dataclass(frozen=True)
class Stall:
    milliseconds: float
    stack: str  # the GUI thread's stack while the stall was going on ("" if it was too short to sample)


class StallWatchdog(QObject):
    def __init__(self, budget_ms: float = BUDGET_MS) -> None:
        super().__init__()
        self.budget = budget_ms / 1000.0
        self.stalls: list[Stall] = []
        self._beat = time.perf_counter()
        self._stack = ""
        self._gui = threading.get_ident()
        self._stop = threading.Event()
        self._timer = QTimer(self)
        self._timer.setInterval(BEAT_MS)
        self._timer.timeout.connect(self._heartbeat)
        self._timer.start()
        self._sampler = threading.Thread(target=self._sample, name="structura-watchdog", daemon=True)
        self._sampler.start()

    @Slot()
    def _heartbeat(self) -> None:
        now = time.perf_counter()
        gap, stack = now - self._beat, self._stack
        self._beat, self._stack = now, ""
        if gap > self.budget:
            self.stalls.append(Stall(gap * 1000.0, stack))

    def _sample(self) -> None:
        while not self._stop.wait(SAMPLE_S):
            if not self._stack and time.perf_counter() - self._beat > self.budget:
                frame = sys._current_frames().get(self._gui)
                self._stack = "".join(traceback.format_stack(frame)) if frame is not None else ""

    def stop(self) -> list[Stall]:
        self._stop.set()
        self._timer.stop()
        return list(self.stalls)
