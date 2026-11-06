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
from collections.abc import Callable
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
