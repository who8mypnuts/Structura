"""Render presets (docs/14 §5.4): Draft, Standard, Final and Print 4K. A preset sets the samples, the size of
the image (its long edge; the aspect follows the viewport), the noise threshold and denoising. Editing the
samples by hand turns the preset into "Custom"."""

from __future__ import annotations

from dataclasses import dataclass

CUSTOM = "Custom"
VIEWPORT_CAP = 1280  # Custom: the viewport's size, but no larger than this


@dataclass(frozen=True)
class Preset:
    name: str
    samples: int
    long_edge: int  # pixels along the image's longer side
    noise_threshold: float  # 0: every pixel gets every sample
    denoise: str


PRESETS = (
    Preset("Draft", 16, 960, 0.0, "auto"),
    Preset("Standard", 128, 1280, 0.02, "auto"),
    Preset("Final", 1024, 1920, 0.005, "auto"),
    Preset("Print 4K", 2048, 3840, 0.003, "auto"),
)
BY_NAME = {p.name: p for p in PRESETS}


def image_size(viewport: tuple[int, int], long_edge: int | None) -> tuple[int, int]:
    """The render size with the viewport's aspect: ``long_edge`` pixels along the longer side (None: the
    viewport's own size, capped at VIEWPORT_CAP)."""
    w, h = max(1, viewport[0]), max(1, viewport[1])
    scale = (long_edge or min(VIEWPORT_CAP, max(w, h))) / max(w, h)
    return max(16, round(w * scale)), max(16, round(h * scale))
