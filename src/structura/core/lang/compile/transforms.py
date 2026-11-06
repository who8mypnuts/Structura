"""Compose a transformation list into one Transform with Structure Synth's 'append' rules (docs/06 §7.1)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from ...color import hsv_ints, parse_color
from ..ast import TransformOp
from . import legacy_math as lm

RANDOM_HUE = 1000.0  # absolute Δh > 360 means "draw from the colour pool"


@dataclass(frozen=True)
class Transform:
    matrix: lm.Mat
    dh: float = 0.0
    ks: float = 1.0
    kv: float = 1.0
    ka: float = 1.0
    absolute: bool = False
    blend_hsv: tuple[float, float, float] = (0.0, 0.0, 0.0)
    strength: float = 0.0
    material: str | None = None  # v2 'mat NAME': the material tag inherited by the subtree

    def append(self, t: Transform) -> Transform:
        matrix = lm.matmul(self.matrix, t.matrix)
        if not (t.absolute and self.absolute):
            f32 = np.float32
            dh, ks = float(f32(self.dh + t.dh)), float(f32(self.ks * t.ks))
            kv, ka = float(f32(self.kv * t.kv)), float(f32(self.ka * t.ka))
            absolute = t.absolute or self.absolute
        else:
            dh, ks, kv, ka, absolute = t.dh, t.ks, t.kv, t.ka, True
        blend, strength = (t.blend_hsv, t.strength) if t.strength != 0 else (self.blend_hsv, self.strength)
        material = t.material if t.material is not None else self.material
        return Transform(matrix, dh, ks, kv, ka, absolute, blend, strength, material)


def _color_hsv(text: str) -> tuple[float, float, float, float]:
    color = parse_color(text)
    assert color is not None  # validated by the parser
    h, s, v, a = hsv_ints(color)
    return float(h), s / 255.0, v / 255.0, a / 255.0


def _color(op: TransformOp) -> Transform:
    text = str(op.args[0])
    if text == "random":
        return Transform(lm.identity(), dh=RANDOM_HUE, absolute=True)
    h, s, v, a = _color_hsv(text)
    return Transform(
        lm.identity(), dh=h, ks=float(np.float32(s)), kv=float(np.float32(v)), ka=float(np.float32(a)), absolute=True
    )


def _blend(op: TransformOp) -> Transform:
    h, s, v, _ = _color_hsv(str(op.args[0]))
    return Transform(lm.identity(), blend_hsv=(h, s, v), strength=float(op.args[1]))


def _numbers(op: TransformOp) -> list[float]:
    return [float(a) for a in op.args]


def _f32(x: float) -> float:
    return float(np.float32(x))


def single(op: TransformOp) -> Transform:
    """The Transform of one operator."""
    n = _numbers(op) if op.name not in ("color", "blend", "mat") else []
    builders: dict[str, Callable[[], Transform]] = {
        "x": lambda: Transform(lm.translation(n[0], 0, 0)),
        "y": lambda: Transform(lm.translation(0, n[0], 0)),
        "z": lambda: Transform(lm.translation(0, 0, n[0])),
        "rx": lambda: Transform(lm.axis_rotation(0, n[0])),
        "ry": lambda: Transform(lm.axis_rotation(1, n[0])),
        "rz": lambda: Transform(lm.axis_rotation(2, n[0])),
        "s": lambda: Transform(lm.scale(n[0], n[0], n[0]) if len(n) == 1 else lm.scale(n[0], n[1], n[2])),
        "matrix": lambda: Transform(lm.matrix3(tuple(n))),
        "reflect": lambda: Transform(lm.plane_reflection(n[0], n[1], n[2])),
        "fx": lambda: Transform(lm.scale(-1, 1, 1)),
        "fy": lambda: Transform(lm.scale(1, -1, 1)),
        "fz": lambda: Transform(lm.scale(1, 1, -1)),
        "hue": lambda: Transform(lm.identity(), dh=_f32(n[0])),
        "sat": lambda: Transform(lm.identity(), ks=_f32(n[0])),
        "brightness": lambda: Transform(lm.identity(), kv=_f32(n[0])),
        "alpha": lambda: Transform(lm.identity(), ka=_f32(n[0])),
        "color": lambda: _color(op),
        "blend": lambda: _blend(op),
        "mat": lambda: Transform(lm.identity(), material=str(op.args[0])),
    }
    return builders[op.name]()


def compose(ops: tuple[TransformOp, ...]) -> Transform:
    result = Transform(lm.identity())
    for op in ops:
        result = result.append(single(op))
    return result
