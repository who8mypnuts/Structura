"""Shared Numba compilation options for Structura's CPU kernels.

Kernels never allocate: every buffer is created by the Python driver. Numba's runtime reference counting
(NRT) is therefore disabled (``_nrt=False``). This is essential, not cosmetic: with NRT enabled, some branch
shapes make Numba incref/decref every array of the namedtuple arguments on every call, about 1 µs per call,
versus about 1 ns without (measured; see docs/PROGRESS.md). ``nogil`` keeps the GUI thread responsive and
``cache`` avoids re-compiling on every start (docs/04 §6).
"""

from __future__ import annotations

import contextlib
import hashlib
import threading
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, cast

from numba import njit

PACKAGE = Path(__file__).resolve().parents[1]
KERNEL_DIRS = ("core/build", "core/rng", "core/color", "render")
STAMP = "structura-kernels.sha1"


def _invalidate_stale_caches() -> None:
    """Numba's on-disk cache keys a function by its own file only, so a kernel that inlines a helper from
    another module keeps stale machine code after that helper changes. Drop every cached kernel of these
    packages whenever any of their sources change."""
    sources = sorted(p for d in KERNEL_DIRS for p in (PACKAGE / d).glob("*.py"))
    digest = hashlib.sha1(b"".join(p.read_bytes() for p in sources)).hexdigest()
    stamp = PACKAGE / "core" / "__pycache__" / STAMP
    with contextlib.suppress(OSError):
        if stamp.exists() and stamp.read_text() == digest:
            return
        for d in KERNEL_DIRS:
            for cached in (PACKAGE / d / "__pycache__").glob("*.nb[ic]"):
                cached.unlink(missing_ok=True)
        stamp.parent.mkdir(parents=True, exist_ok=True)
        stamp.write_text(digest)


_invalidate_stale_caches()


def kernel[F: Callable[..., Any]](fn: F) -> F:
    """Compile ``fn`` as a Structura CPU kernel (nopython, nogil, cached, no reference counting)."""
    return cast(F, njit(cache=True, nogil=True, _nrt=False)(fn))  # type: ignore[call-overload]


def host_kernel[F: Callable[..., Any]](fn: F) -> F:
    """Compile a host-side algorithm that may allocate (BVH build, packing): nopython, nogil, cached, with NRT."""
    return cast(F, njit(cache=True, nogil=True)(fn))


def parallel_kernel[F: Callable[..., Any]](fn: F) -> F:
    """A host algorithm parallelised over CPU cores with ``numba.prange`` (image filters)."""
    return cast(F, njit(cache=True, nogil=True, parallel=True)(fn))


class FairLock:
    """A first-come, first-served lock: a thread that releases and immediately re-acquires (a render loop
    between bands) goes to the back of the queue instead of starving the other lanes."""

    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._next_ticket = 0
        self._serving = 0

    def __enter__(self) -> None:
        with self._cond:
            ticket = self._next_ticket
            self._next_ticket += 1
            self._cond.wait_for(lambda: self._serving == ticket)

    def __exit__(self, *exc: object) -> None:
        with self._cond:
            self._serving += 1
            self._cond.notify_all()


_PARALLEL = FairLock()


@contextlib.contextmanager
def parallel_section() -> Iterator[None]:
    """Serialise parallel Numba calls across threads: Numba's portable ``workqueue`` threading layer is not
    safe for concurrent parallel regions (docs/04 §6). Callers keep each section short (one render band, one
    filter pass) so that lanes interleave fairly."""
    with _PARALLEL:
        yield
