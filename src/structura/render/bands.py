"""Banded dispatch (docs/04 §5.2): a render pass is split into bands of rows so that each dispatch takes
about TARGET_SECONDS. Between bands the caller can check for cancellation, and other lanes get the CPU
(parallel Numba sections are serialised; see core.jit.parallel_section)."""

from __future__ import annotations

import time
from collections.abc import Callable

from ..compute.base import Bound

TARGET_SECONDS = 0.03
ROW_STEP = 8  # the kernel's workgroup height
MAX_GROWTH = 4.0


class Bands:
    """Adapts the band height to the measured dispatch time (asynchronous GPU dispatches grow to one band)."""

    def __init__(self, width: int, height: int, rows: int = 32) -> None:
        self.width, self.height = width, height
        self.rows = min(height, rows)

    def _adapt(self, rows: int, seconds: float) -> None:
        scale = min(MAX_GROWTH, TARGET_SECONDS / max(seconds, 1e-6))
        wanted = max(ROW_STEP, round(rows * scale / ROW_STEP) * ROW_STEP)
        self.rows = min(self.height, wanted)

    def dispatch(self, bound: Bound, between: Callable[[], None] | None = None) -> None:
        """One pass over the whole image, band by band; ``between`` runs after every band."""
        y = 0
        while y < self.height:
            rows = min(self.rows, self.height - y)
            bound.update(row0=y)
            bound.set_grid((self.width, rows, 1))
            started = time.perf_counter()
            bound.dispatch()
            self._adapt(rows, time.perf_counter() - started)
            y += rows
            if between is not None:
                between()
