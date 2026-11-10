"""Placeholder values of the 1.5 TemplateRenderer (docs/15 §5.1), computed in float32 like Vector3f.

Each function returns {placeholder: text} for the placeholders one primitive kind supports.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from ...core.scene.ir import SceneIR, legacy_vectors
from .qt_format import qint, qnum

F32 = np.float32
Vec = np.ndarray  # float32[3]
Values = dict[str, str]


@dataclass(frozen=True)
class TemplateCamera:
    position: tuple[float, float, float] = (0.0, 0.0, 20.0)
    up: tuple[float, float, float] = (0.0, 1.0, 0.0)
    right: tuple[float, float, float] = (1.0, 0.0, 0.0)
    target: tuple[float, float, float] = (0.0, 0.0, 0.0)
    width: int = 640
    height: int = 480
    aspect: float = 640 / 480
    fov: float = 22.0


def _xyz(prefix: str, v: Vec) -> Values:
    return {f"{{{prefix}X}}": qnum(v[0]), f"{{{prefix}Y}}": qnum(v[1]), f"{{{prefix}Z}}": qnum(v[2])}


def _square_length(v: Vec) -> np.float32:
    """Vector3f::sqrLength(): x·x + y·y + z·z, left to right in float32 (no FMA, no pairwise sums)."""
    return F32(F32(F32(v[0] * v[0]) + F32(v[1] * v[1])) + F32(v[2] * v[2]))


def begin_end_values(cam: TemplateCamera, background: tuple[float, float, float]) -> Values:
    pos, up, right, target = (np.asarray(v, F32) for v in (cam.position, cam.up, cam.right, cam.target))
    direction = target - pos
    direction = direction / F32(np.sqrt(_square_length(direction)))
    u, w = -right, -direction
    column = [u[0], up[0], w[0], pos[0], u[1], up[1], w[1], pos[1], u[2], up[2], w[2], pos[2]]
    values = {**_xyz("CamPos", pos), **_xyz("CamUp", up), **_xyz("CamDir", direction)}
    values |= {**_xyz("CamRight", right), **_xyz("CamTarget", target)}
    values["{CamColumnMatrix}"] = " ".join(qnum(x) for x in column) + " 0.0 0.0 0.0 1.0"
    values |= {"{aspect}": qnum(cam.aspect), "{width}": qint(cam.width), "{height}": qint(cam.height)}
    values["{fov}"] = qnum(cam.fov)
    for name, c in zip(("BR", "BG", "BB"), background, strict=True):
        values[f"{{{name}}}"], values[f"{{{name}256}}"] = qnum(c), qnum(c * 255)
    return values


def _color(rgba: np.ndarray, with_rgb: bool = True) -> Values:
    alpha = float(rgba[3])
    values = {"{alpha}": qnum(alpha), "{oneminusalpha}": qnum(1 - alpha)}
    if with_rgb:
        values |= {"{r}": qnum(rgba[0]), "{g}": qnum(rgba[1]), "{b}": qnum(rgba[2])}
    return values


def _frame(scene: SceneIR, i: int) -> tuple[Vec, Vec, Vec, Vec]:
    """(base, dir1, dir2, dir3) as 1.5 handed them to its renderers."""
    return legacy_vectors(scene.xform[i])


def _point(scene: SceneIR, i: int, p: tuple[float, float, float]) -> Vec:
    """M·p in the order of Matrix4f::operator*(Vector3f): ((0 + m0·x) + m1·y) + m2·z, then + m3."""
    m = scene.xform[i].astype(F32)
    out = np.empty(3, F32)
    for row in range(3):
        acc = F32(0.0)
        for col in range(3):
            acc = F32(acc + m[row, col] * F32(p[col]))
        out[row] = F32(acc + m[row, 3])
    return out


def box_values(scene: SceneIR, i: int) -> Values:
    base, d1, d2, d3 = _frame(scene, i)
    nums = [*d1, *d2, *d3, *base]
    matrix = f"{qnum(d1[0])} {qnum(d1[1])} {qnum(d1[2])} 0 {qnum(d2[0])} {qnum(d2[1])} {qnum(d2[2])} 0 " + (
        f"{qnum(d3[0])} {qnum(d3[1])} {qnum(d3[2])} 0 {qnum(base[0])} {qnum(base[1])} {qnum(base[2])} 1"
    )
    cols = [d1[0], d2[0], d3[0], base[0], d1[1], d2[1], d3[1], base[1], d1[2], d2[2], d3[2], base[2]]
    values = {
        "{matrix}": matrix,
        "{columnmatrix}": " ".join(qnum(v) for v in cols) + " 0 0 0 1",
        "{povmatrix}": ", ".join(qnum(v) for v in nums),
    }
    return values | _color(scene.rgba[i])


def sphere_values(scene: SceneIR, i: int) -> Values:
    c = _point(scene, i, (0.5, 0.5, 0.5))
    edge = c - _point(scene, i, (0.5, 0.5, 0.0))
    radius = F32(np.sqrt(_square_length(edge)))
    values = {"{cx}": qnum(c[0]), "{cy}": qnum(c[1]), "{cz}": qnum(c[2]), "{rad}": qnum(float(radius))}
    return values | _color(scene.rgba[i])


def dot_values(scene: SceneIR, i: int) -> Values:
    p = _point(scene, i, (0.5, 0.5, 0.5))
    return {"{x}": qnum(p[0]), "{y}": qnum(p[1]), "{z}": qnum(p[2])} | _color(scene.rgba[i])


def line_values(scene: SceneIR, i: int) -> Values:
    a, b = _point(scene, i, (0.0, 0.5, 0.5)), _point(scene, i, (1.0, 0.5, 0.5))
    values = {"{x1}": qnum(a[0]), "{y1}": qnum(a[1]), "{z1}": qnum(a[2])}
    values |= {"{x2}": qnum(b[0]), "{y2}": qnum(b[1]), "{z2}": qnum(b[2])}
    return values | _color(scene.rgba[i], with_rgb=False)


def triangle_values(scene: SceneIR, i: int) -> Values:
    p = scene.aux_data[scene.aux[i], :9].astype(F32).reshape(3, 3)
    values = {f"{{p{k + 1}{axis}}}": qnum(p[k, j]) for k in range(3) for j, axis in enumerate("xyz")}
    return values | _color(scene.rgba[i], with_rgb=False)


def mesh_values(scene: SceneIR, i: int) -> Values:
    aux = scene.aux_data[scene.aux[i]].astype(F32)
    base, d1, d2, _ = _frame(scene, i)
    parts = [*aux[0:3], *aux[3:6], *aux[6:9], *base, *d1, *d2]
    words = []
    for k, v in enumerate(parts):
        words.append(qnum(v))
        if k % 3 == 2:
            words.append("0" if k < len(parts) - 1 else "1")
    return {"{matrix}": " ".join(words)} | _color(scene.rgba[i])


def solid_values(scene: SceneIR, i: int) -> Values:
    """The v2 solids (cylinder, cone, torus, ellipsoid) fill the unit cube like a box: the box placeholders,
    plus {param} for cone[r] / torus[r] (0 for the others)."""
    return box_values(scene, i) | {"{param}": qnum(float(scene.params(np.array([i]))[0]))}


def tube_values(scene: SceneIR, i: int) -> Values:
    """tube[r]: the line placeholders plus {param} (its diameter in object units) and {r} {g} {b}."""
    param = {"{param}": qnum(float(scene.params(np.array([i]))[0]))}
    return line_values(scene, i) | _color(scene.rgba[i]) | param


VALUES: dict[str, Callable[[SceneIR, int], Values]] = {
    "box": box_values,
    "grid": box_values,
    "sphere": sphere_values,
    "dot": dot_values,
    "line": line_values,
    "triangle": triangle_values,
    "mesh": mesh_values,
    **dict.fromkeys(("cylinder", "cone", "torus", "ellipsoid"), solid_values),
    "tube": tube_values,
}
UID_PREFIX = {
    "box": "Box",
    "grid": "Grid",
    "sphere": "Sphere",
    "dot": "Dot",
    "line": "Line",
    "triangle": "Triangle",
    "mesh": "Box",
    "cylinder": "Cylinder",
    "cone": "Cone",
    "torus": "Torus",
    "ellipsoid": "Ellipsoid",
    "tube": "Tube",
}  # fmt: skip - 1.5 names mesh uids 'Box'
