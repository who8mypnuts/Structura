"""The memory guard (docs/09 §8): a coarse upper estimate of what a render needs, checked against the free
memory before it starts, so a huge image or scene is refused with a message instead of swapping the machine."""

from __future__ import annotations

import psutil

from ..core.scene.ir import SceneIR
from .settings import RenderSettings

PRIM_BYTES = 320  # packed record, inverse transform, bounds and two BVH nodes per primitive (with slack)
TRIANGLE_BYTES = 160  # per aux row (mesh / triangle data) once packed
PIXEL_BYTES = 96  # accumulation, second moment, variance, display and denoiser working copies (float32)
AOV_BYTES = 64  # albedo, normal, depth, ids and their display copies
MIB = 1024 * 1024


def render_bytes(scene: SceneIR, settings: RenderSettings) -> int:
    prims = len(scene) * PRIM_BYTES + int(scene.aux_data.shape[0]) * TRIANGLE_BYTES
    pixel = PIXEL_BYTES + (AOV_BYTES if settings.aovs else 0)
    return prims + settings.width * settings.height * pixel


def available_bytes() -> int:
    return int(psutil.virtual_memory().available)


def guard_message(needed: int, available: int, percent: int) -> str | None:
    """None when ``needed`` fits in ``percent`` % of ``available``; otherwise the refusal to show."""
    allowed = available * max(1, min(100, percent)) // 100
    if needed <= allowed:
        return None
    return (
        f"This render needs about {needed // MIB:,} MB, more than {percent} % of the free memory "
        f"({available // MIB:,} MB). Lower the image size, or raise the memory guard in Preferences ▸ Rendering."
    )
