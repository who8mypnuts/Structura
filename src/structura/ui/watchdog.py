"""UI-stall watchdog (docs/04 §8, docs/18 §7, goal G9): a heartbeat timer on the GUI thread and a sampling
thread. A gap between two beats longer than the budget is a stall; while it is still going on, the sampler
captures the GUI thread's stack, which names the code that blocked the event loop.

In the app (STRUCTURA_WATCHDOG=50) any gap is a stall. Under test, code the test runs itself outside the event
loop also stops the heartbeat; the UI test fixture therefore only counts stalls whose stack shows the event
loop (pytest-qt's wait functions) running.
"""

from __future__ import annotations

import faulthandler
import os
import re
import tempfile
import threading
import time
from dataclasses import dataclass, field

from PySide6.QtCore import QObject, QTimer, Slot

BUDGET_MS = 50.0
BEAT_MS = 10
SAMPLE_S = 0.005
_THREAD = re.compile(r"^(?:Current thread|Thread) (0x[0-9a-f]+)", re.MULTILINE)
_FRAME = re.compile(r'^\s+File "(.*)", line (\d+) in (.*)$', re.MULTILINE)


@dataclass(frozen=True)
class Stall:
    """A gap between heartbeats longer than the budget.

    Attributes:
        milliseconds: The length of the gap.
        stack: The GUI thread's stack while the stall was going on ("" if it was too short to sample).
    """

    milliseconds: float
    stack: str


@dataclass
class _Beat:
    """What the heartbeat and the sampler thread share: a plain object, never the QObject.

    A thread whose target is a bound method of a QObject holds a reference to it; if the thread dropped the
    last one, the QObject would be destroyed on that thread — and PySide's destructor (Qt's connection lock,
    then the GIL) deadlocks against the GUI thread (the GIL, then that lock).

    Attributes:
        budget: The stall budget in seconds.
        gui: The GUI thread's ident.
        last: When the last heartbeat ran (perf_counter seconds).
        stack: The GUI thread's stack sampled during the current gap, or "".
        stop: Set to end the sampler.
    """

    budget: float
    gui: int
    last: float = field(default_factory=time.perf_counter)
    stack: str = ""
    stop: threading.Event = field(default_factory=threading.Event)


def _sample(beat: _Beat) -> None:
    """The sampler thread: captures the GUI thread's stack once per gap longer than the budget.

    The stack comes from faulthandler, which walks the interpreter's frames natively. `sys._current_frames()`
    would hand this thread references to the GUI thread's frame objects; when the GUI thread has returned from
    them, this thread drops the last reference, and the frames' locals (PySide objects among them) are
    destroyed here — PySide's destructors then take Qt's locks and the GIL in the order that deadlocks
    against the GUI thread.

    Args:
        beat: The state shared with the heartbeat; `beat.stack` receives the sample.
    """
    with tempfile.TemporaryFile() as dump:
        while not beat.stop.wait(SAMPLE_S):
            if not beat.stack and time.perf_counter() - beat.last > beat.budget:
                beat.stack = _thread_stack(dump.fileno(), beat.gui)


def _thread_stack(fd: int, ident: int) -> str:
    """One thread's stack, in the format (and the order, oldest call first) of `traceback.format_stack`.

    Args:
        fd: A scratch file descriptor faulthandler writes every thread's stack to.
        ident: The thread whose stack to return (`threading.get_ident()`).

    Returns:
        The stack without source lines (faulthandler keeps the 100 most recent calls), or "" if the thread
        was not found.
    """
    os.ftruncate(fd, 0)
    os.lseek(fd, 0, os.SEEK_SET)
    faulthandler.dump_traceback(fd, all_threads=True)
    size = os.lseek(fd, 0, os.SEEK_CUR)
    os.lseek(fd, 0, os.SEEK_SET)
    text = os.read(fd, size).decode("utf-8", "replace")
    heads = list(_THREAD.finditer(text))
    for head, after in zip(heads, [*heads[1:], None], strict=True):
        if int(head.group(1), 16) == ident:
            section = text[head.end() : after.start() if after else len(text)]
            frames = reversed(_FRAME.findall(section))
            return "".join(f'  File "{path}", line {line}, in {name}\n' for path, line, name in frames)
    return ""


class StallWatchdog(QObject):
    """Counts stalls of the GUI thread (gaps between heartbeats longer than a budget) with their stacks."""

    def __init__(self, budget_ms: float = BUDGET_MS) -> None:
        """Starts the heartbeat and the sampler.

        Args:
            budget_ms: The longest acceptable gap between two heartbeats.
        """
        super().__init__()
        self.stalls: list[Stall] = []
        self._beat = _Beat(budget_ms / 1000.0, threading.get_ident())
        self._timer = QTimer(self)
        self._timer.setInterval(BEAT_MS)
        self._timer.timeout.connect(self._heartbeat)
        self._timer.start()
        self._sampler = threading.Thread(target=_sample, args=(self._beat,), name="structura-watchdog", daemon=True)
        self._sampler.start()

    @Slot()
    def _heartbeat(self) -> None:
        beat, now = self._beat, time.perf_counter()
        gap, stack = now - beat.last, beat.stack
        beat.last, beat.stack = now, ""
        if gap > beat.budget:
            self.stalls.append(Stall(gap * 1000.0, stack))

    def stop(self) -> list[Stall]:
        """Stops the heartbeat and the sampler (waiting for it to end).

        Returns:
            Every stall seen.
        """
        self._beat.stop.set()
        self._timer.stop()
        self._sampler.join()
        return list(self.stalls)
