"""'set raytracer::KEY value' → RenderSettings (docs/05 §6.3, docs/10 §6.1).

Structure Synth parsed these with MiniParser: comma-separated values after removing '[' and ']'. Unknown or
malformed values are ignored here; the linter reports them.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from dataclasses import replace
from typing import Any

from ..core.scene.camera import Camera, LegacyView
from .settings import RenderSettings

NEAR, FAR = 5.0, 60.0  # the legacy OpenGL clip planes the 1.5 raytracer unprojected through


def _floats(value: str) -> list[float]:
    return [float(p) for p in value.replace(",", " ").split()]


def _bool(value: str) -> bool:
    return value.strip().lower() in ("true", "1", "yes", "on")


def _size(value: str) -> dict[str, Any]:
    w, _, h = value.lower().partition("x")
    width, height = int(w or 0), int(h or 0)
    if width <= 0 and height <= 0:
        return {}
    return {"width": width, "height": height}


KEYS: dict[str, Callable[[str], dict[str, Any]]] = {
    "samples": lambda v: {"samples": max(1, int(_floats(v)[0])) ** 2},
    "ambient-occlusion-samples": lambda v: {"ao_samples": max(0, int(_floats(v)[0])) ** 2},
    "max-depth": lambda v: {"max_bounces": max(0, int(_floats(v)[0]))},
    "dof": lambda v: {"legacy_dof": (_floats(v)[0], _floats(v)[1])},
    "shadows": lambda v: {"shadows": _bool(v)},
    "light": lambda v: {"light_position": tuple(_floats(v)[:3])},
    "size": _size,
}


def legacy_overrides(raytracer: Iterable[tuple[str, str]]) -> dict[str, Any]:
    """Settings fields set by the script, in execution order (later keys win)."""
    out: dict[str, Any] = {}
    for key, value in raytracer:
        handler = KEYS.get(key.lower())
        if handler is None:
            continue
        try:
            out |= handler(value)
        except (ValueError, IndexError):
            continue
    return out


def complete_size(width: int, height: int, aspect: float) -> tuple[int, int]:
    """'size [Wx0]' / '[0xH]' keep the window aspect ratio, as in 1.5."""
    if width <= 0:
        width = round(height * aspect)
    if height <= 0:
        height = round(width / aspect)
    return width, height


def with_legacy(settings: RenderSettings, raytracer: Iterable[tuple[str, str]]) -> RenderSettings:
    overrides = legacy_overrides(raytracer)
    if "width" in overrides:
        overrides["width"], overrides["height"] = complete_size(overrides["width"], overrides["height"], 4 / 3)
    return replace(settings, **overrides)


def legacy_lens(view: LegacyView, dof: tuple[float, float]) -> tuple[float, float]:
    """(aperture radius, focus distance) of the thin lens equivalent to 'dof [center, falloff]'."""
    center, falloff = dof
    h_near = 2.0 * NEAR * math.tan(math.radians(view.fov_y_deg) / 2.0)
    return falloff * h_near / view.scale, (NEAR + (FAR - NEAR) * center) / view.scale


def default_light(
    camera: Camera, aspect: float, world_per_view: float, reference_height: float = 600.0
) -> tuple[float, float, float]:
    """1.5's light: the near-plane point 200 px left of the window's top-left corner (docs/10 §2.1).

    ``world_per_view`` is 1/scale of the legacy view (view-space units → world units).
    """
    forward, right, up = camera.basis
    width = reference_height * aspect
    tan_half = math.tan(math.radians(camera.fov_y_deg) / 2.0)
    ndc_x = 2.0 * (-200.0) / width - 1.0
    x_v, y_v = ndc_x * NEAR * tan_half * aspect, NEAR * tan_half
    p = camera.eye + (right * x_v + up * y_v + forward * NEAR) * world_per_view
    return (float(p[0]), float(p[1]), float(p[2]))
