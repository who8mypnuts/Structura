"""Small preview renders of a scene or a script (docs/14 §3, §5.3): example gallery tiles, variation cells.

The 'preview' integrator on the CPU backend: quick, deterministic, and independent of the GPU lanes.
"""

from __future__ import annotations

import numpy as np

from ..compute.cpu import CpuBackend
from ..core.build.api import build_capped
from ..core.lang.api import compile_script
from ..core.scene.ir import SceneIR
from .api import render
from .output import to_display
from .settings import RenderSettings

MAX_OBJECTS = 60_000  # enough to recognise any example; keeps each thumbnail well under a second


def thumbnail_rgb(scene: SceneIR, size: tuple[int, int], samples: int = 2) -> np.ndarray:
    """uint8[H, W, 3]: the framed scene, or a black tile for an empty one."""
    if not len(scene):
        return np.zeros((size[1], size[0], 3), np.uint8)
    settings = RenderSettings(width=size[0], height=size[1], samples=samples, samples_per_pass=samples,
                              integrator="preview", frame=True)  # fmt: skip
    return to_display(render(scene, settings, CpuBackend()).image, 0.0, "soft")


def script_thumbnail(text: str, size: tuple[int, int], seed: int = 0) -> tuple[np.ndarray, int]:
    """(image, objects) for an EisenScript text; the build stops at MAX_OBJECTS."""
    scene = build_capped(compile_script(text, seed).program, seed, MAX_OBJECTS)
    return thumbnail_rgb(scene, size), len(scene)
