"""Pack v2 point / sphere / spot lights into 'light_f' records (layout: render/kernels/layout.py).

Radiant intensity I = power / 4π × colour (linear), so a light's 'power' is comparable across types.
"""

from __future__ import annotations

import math

import numpy as np

from ..core.color import parse_color, srgb_to_linear
from ..core.scene.declarations import LightSpec, SceneDeclarations
from .kernels import layout as lay


def _vec(value: object, default: tuple[float, float, float]) -> np.ndarray:
    if isinstance(value, tuple) and len(value) == 3:
        return np.asarray(value, np.float32)
    return np.asarray(default, np.float32)


def _colour(value: object) -> np.ndarray:
    c = parse_color(str(value)) if value is not None else None
    rgb = np.array([c.r, c.g, c.b], np.float32) / np.float32(65535) if c else np.ones(3, np.float32)
    return srgb_to_linear(rgb)


def pack_light(light: LightSpec) -> np.ndarray:
    r = np.zeros(lay.LIGHT_F, np.float32)
    v = light.values
    position = _vec(v.get("position"), (0.0, 10.0, 0.0))
    r[lay.L_TYPE] = lay.LIGHT_TYPES[light.type]
    r[lay.L_POS : lay.L_POS + 3] = position
    r[lay.L_RADIUS] = float(v.get("radius", 0.0)) if light.type == "sphere" else 0.0
    r[lay.L_INTENSITY : lay.L_INTENSITY + 3] = _colour(v.get("color")) * float(v.get("power", 100.0)) / (4 * math.pi)
    if light.type == "spot":
        axis = _vec(v.get("target"), (0.0, 0.0, 0.0)) - position
        r[lay.L_DIR : lay.L_DIR + 3] = axis / (np.linalg.norm(axis) or 1.0)
        outer = math.radians(float(v.get("cone", 30.0)))
        r[lay.L_COS_OUTER] = math.cos(outer)
        r[lay.L_COS_INNER] = math.cos(outer * (1.0 - float(v.get("blend", 0.2))))
    return r


def pack_lights(decl: SceneDeclarations | None) -> np.ndarray:
    """float32[max(1, L), LIGHT_F] for every non-sun light (the sun lives in cfg)."""
    lights = [light for light in (decl.lights if decl else ()) if light.type in lay.LIGHT_TYPES]
    if not lights:
        return np.zeros((1, lay.LIGHT_F), np.float32)
    return np.stack([pack_light(light) for light in lights])


def light_count(decl: SceneDeclarations | None) -> int:
    return sum(1 for light in (decl.lights if decl else ()) if light.type in lay.LIGHT_TYPES)
