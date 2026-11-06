"""Pass sizing for progressive renders (docs/09 §3).

A pass is one dispatch of every band followed by a read-back, tone mapping and an image update. Fixed pass
sizes (``samples_per_pass > 0``) keep renders reproducible; ``samples_per_pass = 0`` ("auto") starts with a
single sample for a fast first image and then grows the passes until each one takes about TARGET_SECONDS of
device time, so the per-pass host work stays small next to the GPU work.
"""

from __future__ import annotations

from .settings import RenderSettings

TARGET_SECONDS = 0.4
MAX_GROWTH = 4.0
MAX_SAMPLES_PER_PASS = 64


class Pacing:
    def __init__(self, settings: RenderSettings) -> None:
        self.settings = settings
        self.auto = settings.samples_per_pass <= 0
        self.spp = max(1, settings.samples_per_pass)

    def next(self, done: int) -> int:
        """Samples for the pass starting at ``done``; adaptive renders stop exactly at adaptive_min_samples first."""
        s = self.settings
        spp = min(self.spp, s.samples - done)
        if s.noise_threshold > 0 and done < s.adaptive_min_samples:
            spp = min(spp, s.adaptive_min_samples - done)
        return max(1, spp)

    def observe(self, spp: int, seconds: float) -> None:
        """Record how long a pass of ``spp`` samples took on the device."""
        if self.auto:
            scale = min(MAX_GROWTH, TARGET_SECONDS / max(seconds, 1e-6))
            self.spp = max(1, min(MAX_SAMPLES_PER_PASS, int(spp * scale)))
