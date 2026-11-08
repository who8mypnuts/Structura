"""Adaptive preview quality (docs/08 §5 "adaptive quality"): while the camera moves, frames skip SSAO when a
full-quality frame took longer than the budget on the GPU; still frames (the AA accumulation) are full quality.

The GPU time comes from a timer query around full-quality frames, read one frame later (by then it is done,
so reading does not stall the pipeline).
"""

from __future__ import annotations

from contextlib import AbstractContextManager, nullcontext
from typing import Any

SLOW_FRAME_MS = 22.0  # above this, moving frames drop SSAO (a 45 fps floor on a 60 Hz display)


class AdaptiveQuality:
    def __init__(self, ctx: Any) -> None:
        self.query: Any = None
        try:
            self.query = ctx.query(time=True)
        except Exception:  # no timer queries (GL ES, some drivers): always full quality
            self.query = None
        self._pending = False
        self.full_ms = 0.0

    def reduced(self, moving: bool) -> bool:
        """Whether this frame should be cheap: the camera moves and full frames are known to be slow."""
        if self._pending and self.query is not None:
            self.full_ms = float(self.query.elapsed) / 1e6
            self._pending = False
        return moving and self.full_ms > SLOW_FRAME_MS

    def measure(self, reduced: bool) -> AbstractContextManager[Any]:
        """Wraps a frame's GPU work; only full-quality frames are timed."""
        if reduced or self.query is None:
            return nullcontext()
        self._pending = True
        return self.query  # type: ignore[no-any-return]

    def release(self) -> None:
        self.query = None  # moderngl queries have no release(); the context frees them
