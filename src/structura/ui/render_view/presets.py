"""Render presets (docs/14 §5.4): Draft, Standard, Final and Print 4K. A preset sets the samples, the size of
the image (its long edge), the noise threshold and denoising. Editing the samples by hand turns the preset into
"Custom".

The frame (PLAN QoL-2) decides the image's shape: the viewport's, the script's 'render { size }', a ratio
(16:9 …) with the preset's long edge, or an exact custom size. A frame wider than the viewport keeps the
viewport's horizontal view (the camera's vertical field is narrowed to fit), so the viewport's frame guide
shows exactly what the render will contain."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from ...core.scene.camera import Camera

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


FRAME_VIEWPORT, FRAME_SCRIPT, FRAME_CUSTOM = "Viewport", "Script", "Custom"
RATIOS = {"16:9": 16 / 9, "3:2": 1.5, "4:3": 4 / 3, "1:1": 1.0, "4:5": 0.8, "9:16": 9 / 16}
FRAMES = (FRAME_VIEWPORT, FRAME_SCRIPT, *RATIOS, FRAME_CUSTOM)


def image_size(viewport: tuple[int, int], long_edge: int | None) -> tuple[int, int]:
    """The render size with the viewport's aspect: ``long_edge`` pixels along the longer side (None: the
    viewport's own size, capped at VIEWPORT_CAP)."""
    w, h = max(1, viewport[0]), max(1, viewport[1])
    scale = (long_edge or min(VIEWPORT_CAP, max(w, h))) / max(w, h)
    return max(16, round(w * scale)), max(16, round(h * scale))


def frame_size(
    frame: str, viewport: tuple[int, int], long_edge: int | None, script: tuple[int, int], custom: tuple[int, int]
) -> tuple[int, int]:
    """Returns the render size for a FRAMES choice.

    Args:
        frame: The choice: 'Viewport', 'Script', a ratio ('16:9') or 'Custom'.
        viewport: The viewport's size in pixels.
        long_edge: The preset's long edge (None: the viewport's, capped at VIEWPORT_CAP).
        script: The script's size (used as it is for 'Script').
        custom: The custom size (used as it is for 'Custom').
    """
    if frame == FRAME_SCRIPT:
        return script
    if frame == FRAME_CUSTOM:
        return custom
    ratio = RATIOS.get(frame)
    if ratio is None:
        return image_size(viewport, long_edge)
    edge = long_edge or min(VIEWPORT_CAP, max(1, *viewport))
    return (edge, max(16, round(edge / ratio))) if ratio >= 1.0 else (max(16, round(edge * ratio)), edge)


def fitted(camera: Camera, render_aspect: float, view_aspect: float) -> Camera:
    """Returns the camera a render uses when its aspect differs from the viewport's.

    The vertical field stays, unless the render is wider than the viewport: then the horizontal field stays (the
    frame guide's letterbox shows exactly that).

    Args:
        camera: The viewport's camera.
        render_aspect: The render's width / height.
        view_aspect: The viewport's width / height.
    """
    if render_aspect <= view_aspect or view_aspect <= 0:
        return camera
    tan_half = math.tan(math.radians(camera.fov_y_deg) / 2) * view_aspect / render_aspect
    return replace(camera, fov_y_deg=math.degrees(2 * math.atan(tan_half)))


def guide_rect(render_aspect: float, size: tuple[int, int]) -> tuple[float, float, float, float]:
    """Returns (x, y, width, height) of the render frame inside the viewport (see ``fitted``).

    Args:
        render_aspect: The render's width / height.
        size: The viewport's size in pixels.
    """
    w, h = max(1, size[0]), max(1, size[1])
    if render_aspect <= w / h:
        width = h * render_aspect
        return (w - width) / 2, 0.0, width, float(h)
    height = w / render_aspect
    return 0.0, (h - height) / 2, float(w), height
