"""What a render yields after every pass (or bucket), and the state a render loop carries (docs/09 §5)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np

from ..compute.base import Bound
from .aovs import Aovs
from .film import film_image
from .settings import RenderSettings

Rect = tuple[int, int, int, int]  # x0, y0, x1, y1 (pixels, exclusive end)


@dataclass(frozen=True)
class RenderProgress:
    """A render's state after a pass: the image and what the reports and the Render view need.

    Attributes:
        image: float32 (H, W, 3) linear radiance estimate.
        samples: The most samples any pixel has.
        seconds: Render time so far (earlier sessions of a resumed render included).
        aovs: First-hit channels, when the settings ask for them.
        sample_map: int32 (H, W) samples per pixel (adaptive sampling varies them).
        active: The fraction of pixels still being sampled.
        film: The raw accumulation buffer (to resume a stopped render).
        mask: uint32 pixel mask still being sampled (to resume).
        tile: Tiled sampler: the bucket rendered next (the Render view marks it).
        completed: Tiled sampler: the fraction of buckets done (None for the progressive sampler).
        pass_seconds: Time of every pass (or bucket) so far (reports).
        kernel_seconds: Time to bind the render kernel: its first compile on a device, else an upload.
    """

    image: np.ndarray
    samples: int
    seconds: float
    aovs: Aovs | None = None
    sample_map: np.ndarray | None = None
    active: float = 1.0
    film: np.ndarray | None = None
    mask: np.ndarray | None = None
    tile: Rect | None = None
    completed: float | None = None
    pass_seconds: tuple[float, ...] = ()
    kernel_seconds: float = 0.0


@dataclass
class RenderRun:
    """A render in progress: the bound kernel and the per-pixel bookkeeping shared by both samplers."""

    settings: RenderSettings
    bound: Bound
    mask: np.ndarray  # uint32 (H·W): pixels still being sampled
    counts: np.ndarray  # int32 (H, W): samples per pixel
    done: int  # samples every active pixel has (progressive)
    spent: float  # seconds of earlier sessions (resume)
    aovs: Aovs | None = None
    started: float = field(default_factory=time.perf_counter)
    bind_seconds: float = 0.0
    pass_times: list[float] = field(default_factory=list)

    @property
    def size(self) -> tuple[int, int]:
        return self.settings.width, self.settings.height

    @property
    def seconds(self) -> float:
        return self.spent + time.perf_counter() - self.started

    def out_of_time(self) -> bool:
        return 0 < self.settings.time_limit <= self.seconds

    def sample_base(self, done: int) -> int:
        return self.settings.seed * 1_000_003 + done

    def snapshot(self, accum: np.ndarray, **extra: Any) -> RenderProgress:
        """Returns the progress for an accumulation buffer.

        Args:
            accum: The film as read back from the device.
            **extra: RenderProgress fields to set (the tiled sampler's bucket and completion).
        """
        w, h = self.size
        snapshot = RenderProgress(film_image(accum, w, h), int(self.counts.max(initial=0)), self.seconds, self.aovs,
                                  self.counts.copy(), float(self.mask.mean()), accum, self.mask.copy(),
                                  pass_seconds=tuple(self.pass_times), kernel_seconds=self.bind_seconds)  # fmt: skip
        return replace(snapshot, **extra) if extra else snapshot
