"""Small preview renders of a scene or a script (docs/14 §3, §5.3): example gallery tiles, variation cells.

The 'preview' integrator on the CPU backend: quick, deterministic, and independent of the GPU lanes. Gallery
tiles (``script_view``) show the script as it was meant: its own camera, background or sky, and look; rule
previews and variation cells frame the structure instead, so each cell shows all of it.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from ..compute.cpu import CpuBackend
from ..core.build.api import build_capped
from ..core.lang.api import compile_script
from ..core.scene.ir import SceneIR
from .api import render, script_settings
from .output import Display

MAX_OBJECTS = 60_000  # enough to recognise any example; keeps each thumbnail well under a second
FRAMED = Display(0.0, "soft")


def thumbnail_rgb(scene: SceneIR, size: tuple[int, int], samples: int = 2, script_view: bool = False) -> np.ndarray:
    """uint8[H, W, 3]: the scene (framed, or seen by its own camera), or a black tile for an empty one."""
    if not len(scene):
        return np.zeros((size[1], size[0], 3), np.uint8)
    settings = replace(script_settings(scene), width=size[0], height=size[1], samples=samples,
                       samples_per_pass=samples, integrator="preview", frame=not script_view, aovs=False)  # fmt: skip
    display = replace(settings.display, view="soft") if script_view else FRAMED
    return display.apply(render(scene, settings, CpuBackend()).image)


def script_thumbnail(
    text: str, size: tuple[int, int], seed: int = 0, script_view: bool = False
) -> tuple[np.ndarray, int]:
    """(image, objects) for an EisenScript text; the build stops at MAX_OBJECTS."""
    scene = build_capped(compile_script(text, seed).program, seed, MAX_OBJECTS)
    return thumbnail_rgb(scene, size, script_view=script_view), len(scene)
