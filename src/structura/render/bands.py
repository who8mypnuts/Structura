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
    """Adapts the band height to the measured dispatch time."""

    def __init__(self, width: int, height: int, rows: int = 32) -> None:
        self.width, self.height = width, height
        self.rows = min(height, rows)

    def _adapt(self, rows: int, seconds: float) -> None:
        scale = min(MAX_GROWTH, TARGET_SECONDS / max(seconds, 1e-6))
        wanted = max(ROW_STEP, round(rows * scale / ROW_STEP) * ROW_STEP)
        self.rows = min(self.height, wanted)

    def dispatch(self, bound: Bound, between: Callable[[], None] | None = None) -> float:
        """One pass over the whole image, band by band; ``between`` runs after every band. Each band is waited
        for (Bound.finish), so the timing is real device time and no submission monopolises a display GPU.
        Returns the pass's device seconds."""
        y, total = 0, 0.0
        while y < self.height:
            rows = min(self.rows, self.height - y)
            bound.update(row0=y)
            bound.set_grid((self.width, rows, 1))
            started = time.perf_counter()
            bound.dispatch()
            bound.finish()
            seconds = time.perf_counter() - started
            self._adapt(rows, seconds)
            y, total = y + rows, total + seconds
            if between is not None:
                between()
        return total
