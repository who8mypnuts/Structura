"""Job, JobContext and friends (docs/04 §2). Domain code runs inside ``Job.run`` and sees only the context."""

from __future__ import annotations

import threading
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol


class Lane(Enum):
    ANALYSIS = "analysis"
    BUILD = "build"
    COMPUTE = "compute"  # the only lane allowed to run parallel Numba kernels (docs/04 §6)
    DEVICE = "device"  # owns the precision engine's compute device
    IO = "io"


class JobCancelled(Exception):  # noqa: N818 - a normal outcome, not an error
    """Raised by JobContext.check_cancelled(); never reported as a failure."""


@dataclass(frozen=True)
class ErrorInfo:
    message: str
    details: str = ""

    @classmethod
    def from_exception(cls, exc: BaseException) -> ErrorInfo:
        return cls(f"{type(exc).__name__}: {exc}", "".join(traceback.format_exception(exc)))


class Job(Protocol):
    name: str
    lane: Lane
    key: str | None  # latest-wins coalescing key

    def run(self, ctx: JobContext) -> Any: ...


@dataclass
class FunctionJob:
    """A Job from a plain function of the context."""

    name: str
    lane: Lane
    fn: Callable[[JobContext], Any]
    key: str | None = None

    def run(self, ctx: JobContext) -> Any:
        return self.fn(ctx)


class JobContext:
    """Thread-safe view of a running job: cancellation, throttled progress and streaming partial results."""

    PROGRESS_INTERVAL = 1 / 30

    def __init__(self, emit_progress: Callable[[float, str], None], emit_partial: Callable[[object], None]) -> None:
        self._cancel = threading.Event()
        self._emit_progress, self._emit_partial = emit_progress, emit_partial
        self._last_progress = 0.0

    def cancel(self) -> None:
        self._cancel.set()

    @property
    def cancelled(self) -> bool:
        return self._cancel.is_set()

    def check_cancelled(self) -> None:
        if self._cancel.is_set():
            raise JobCancelled

    def progress(self, fraction: float, text: str = "", force: bool = False) -> None:
        now = time.monotonic()
        if force or now - self._last_progress >= self.PROGRESS_INTERVAL:
            self._last_progress = now
            self._emit_progress(float(fraction), text)

    def partial(self, payload: object) -> None:
        """Stream an immutable intermediate result (build chunks, render passes)."""
        self._emit_partial(payload)
