"""Pack v2 point / sphere / spot lights into 'light_f' records (layout: render/kernels/layout.py).

Radiant intensity I = power / 4π × colour (linear), so a light's 'power' is comparable across types.
"""

from __future__ import annotations

import math

import numpy as np

from ..core.color import linear_of
from ..core.scene.declarations import LightSpec, SceneDeclarations, Values
from ..core.scene.vectors import Vec3, vec3_of
from .kernels import layout as lay


def _vec(value: object, default: Vec3) -> np.ndarray:
    return np.asarray(vec3_of(value, default), np.float32)


def _colour(value: object) -> np.ndarray:
    return np.asarray(linear_of(value, (1.0, 1.0, 1.0)), np.float32)


def _rect(r: np.ndarray, v: Values, position: np.ndarray) -> None:
    """One-sided rectangle facing 'target': centre, half-edges, area and radiance L = P·colour / (π·A)."""
    target = _vec(v.get("target"), tuple(position - np.array([0.0, 1.0, 0.0], np.float32)))
    normal = target - position
    normal = normal / (np.linalg.norm(normal) or 1.0)
    hint = np.array([0.0, 1.0, 0.0] if abs(normal[1]) < 0.9 else [1.0, 0.0, 0.0], np.float32)
    u = np.cross(normal, hint)
    u /= np.linalg.norm(u)
    w, h = _size(v.get("size"))
    eu, ev = u * (w / 2), np.cross(normal, u) * (h / 2)  # cross(eu, ev) points along the normal
    area = w * h
    r[lay.L_DIR : lay.L_DIR + 3], r[lay.L_EDGE_V : lay.L_EDGE_V + 3], r[lay.L_RADIUS] = eu, ev, area
    r[lay.L_INTENSITY : lay.L_INTENSITY + 3] = (
        _colour(v.get("color")) * float(v.get("power", 100.0)) / (math.pi * max(area, 1e-9))
    )


def _size(value: object) -> tuple[float, float]:
    if isinstance(value, tuple) and len(value) >= 2:
        return float(value[0]), float(value[1])
    if isinstance(value, float):
        return value, value
    return 1.0, 1.0


def pack_light(light: LightSpec) -> np.ndarray:
    r = np.zeros(lay.LIGHT_F, np.float32)
    v = light.values
    position = _vec(v.get("position"), (0.0, 10.0, 0.0))
    r[lay.L_TYPE] = lay.LIGHT_TYPES[light.type]
    r[lay.L_POS : lay.L_POS + 3] = position
    r[lay.L_RADIUS] = float(v.get("radius", 0.0)) if light.type == "sphere" else 0.0
    r[lay.L_INTENSITY : lay.L_INTENSITY + 3] = _colour(v.get("color")) * float(v.get("power", 100.0)) / (4 * math.pi)
    if light.type == "rect":
        _rect(r, v, position)
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
