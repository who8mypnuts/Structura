"""Structure Synth 1.5's OBJ export, reproduced byte for byte (ObjRenderer; docs/15 §3 'legacy layout').

Every quirk is kept, because legacy users diff these files: per-primitive vertex de-duplication, the
unit-sphere tessellation with a float 3.1415 degree constant, grid 'l' segments that run one vertex past
their quad (``j+1 % 4``), and normal indices that the de-duplication step invents for line faces.
"""

from __future__ import annotations

import math
from collections.abc import Iterator
from dataclasses import dataclass, field

import numpy as np

from ..core.scene.ir import PrimitiveKind as K
from ..core.scene.ir import SceneIR, legacy_vectors
from .templates.placeholders import _point, _square_length
from .templates.qt_format import qnum

F32 = np.float32
V3 = tuple[float, float, float]
NO_NORMAL = -1
LEGACY_KINDS = frozenset((K.BOX, K.GRID, K.SPHERE, K.MESH, K.LINE, K.DOT, K.TRIANGLE))  # what 1.5 exported
DTOR = float(F32(3.1415 / 180.0))


def _v(a: np.ndarray) -> V3:
    return (float(a[0]), float(a[1]), float(a[2]))


def _add(*vs: np.ndarray) -> np.ndarray:
    out = vs[0].astype(F32)
    for v in vs[1:]:
        out = out + v
    return out


@dataclass
class ObjGroup:
    name: str = ""
    vertices: list[V3] = field(default_factory=list)
    normals: list[V3] = field(default_factory=list)
    faces: list[list[list[int]]] = field(default_factory=list)  # [vID, nID] pairs, 1-based

    def add_group(self, g: ObjGroup) -> None:
        nv, nn = len(self.vertices), len(self.normals)
        self.vertices += g.vertices
        self.normals += g.normals
        self.faces += [[[v + nv, n + nn] for v, n in face] for face in g.faces]

    def reduce_vertices(self) -> None:
        vmap, vs = _dedupe(self.vertices)
        nmap, ns = _dedupe(self.normals)
        for face in self.faces:
            for pair in face:
                pair[0] = vmap.get(pair[0] - 1, 0) + 1
                pair[1] = nmap.get(pair[1] - 1, 0) + 1  # QMap::operator[] inserts 0 for unknown keys
        self.vertices, self.normals = vs, ns


def _dedupe(items: list[V3]) -> tuple[dict[int, int], list[V3]]:
    first: dict[V3, int] = {}
    unique: list[V3] = []
    mapping: dict[int, int] = {}
    for i, item in enumerate(items):
        if item not in first:
            first[item] = len(unique)
            unique.append(item)
        mapping[i] = first[item]
    return mapping, unique


def _quad(g: ObjGroup, v1: np.ndarray, v2: np.ndarray, v3: np.ndarray, v4: np.ndarray) -> None:
    vi, vn = len(g.vertices) + 1, len(g.normals) + 1
    g.vertices += [_v(v1), _v(v2), _v(v3), _v(v4)]
    a, b = v2 - v1, v4 - v1
    cross = np.array([a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]], F32)
    inv = F32(1.0 / float(F32(np.sqrt(_square_length(cross)))))
    g.normals += [_v(cross * inv)] * 4
    g.faces.append([[vi + j, vn + j] for j in range(4)])


def _line_quad(g: ObjGroup, v1: np.ndarray, v2: np.ndarray, v3: np.ndarray, v4: np.ndarray) -> None:
    vi = len(g.vertices) + 1
    g.vertices += [_v(v1), _v(v2), _v(v3), _v(v4)]
    g.faces += [[[vi + j, NO_NORMAL], [vi + j + 1, NO_NORMAL]] for j in range(4)]  # 1.5: vi+(j+1 % 4)


def _box_faces(o: np.ndarray, v1: np.ndarray, v2: np.ndarray, v3: np.ndarray) -> list[tuple[np.ndarray, ...]]:
    return [
        (o, _add(o, v2), _add(o, v2, v1), _add(o, v1)),
        (_add(o, v3), _add(o, v1, v3), _add(o, v2, v1, v3), _add(o, v2, v3)),
        (o, _add(o, v3), _add(o, v3, v2), _add(o, v2)),
        (_add(o, v1), _add(o, v2, v1), _add(o, v3, v2, v1), _add(o, v3, v1)),
        (o, _add(o, v1), _add(o, v3, v1), _add(o, v3)),
        (_add(o, v2), _add(o, v3, v2), _add(o, v3, v2, v1), _add(o, v1, v2)),
    ]


def _mesh_faces(aux: np.ndarray, end: np.ndarray, u1: np.ndarray, u2: np.ndarray) -> list[tuple[np.ndarray, ...]]:
    o, v1, v2 = aux[0:3], aux[3:6], aux[6:9]
    v3 = end - o
    return [
        (o, _add(o, v2), _add(o, v2, v1), _add(o, v1)),
        (_add(o, v3), _add(o, u1, v3), _add(o, u2, u1, v3), _add(o, u2, v3)),
        (o, _add(o, v3), _add(o, v3, u2), _add(o, v2)),
        (_add(o, v1), _add(o, v2, v1), _add(o, v3, u2, u1), _add(o, v3, u1)),
        (o, _add(o, v1), _add(o, v3, u1), _add(o, v3)),
        (_add(o, v2), _add(o, v3, u2), _add(o, v3, u2, u1), _add(o, v1, v2)),
    ]


def _unit_sphere_point(theta: float, phi: float) -> np.ndarray:
    ct = math.cos(theta * DTOR)
    return np.array([ct * math.cos(phi * DTOR), ct * math.sin(phi * DTOR), math.sin(theta * DTOR)], F32)


def _sphere(centre: np.ndarray, radius: np.float32, dt: int, dp: int) -> ObjGroup:
    """Paul Bourke's unit sphere as 1.5 built it; vertices are T(c)·S(r)·p evaluated in float32."""
    g = ObjGroup()
    dtheta, dphi = 180.0 / dt, 360.0 / dp

    def place(p: np.ndarray) -> np.ndarray:  # ((0 + s·p) + 0 + 0) + c per row, as Matrix4f · Vector3f
        out: np.ndarray = F32(0.0) + radius * p + centre
        return out

    for i in range(dt):
        theta = -90.0 + (i * 180.0) / dt
        for j in range(dp):
            phi = (j * 360.0) / dp
            points = [_unit_sphere_point(theta, phi)]
            if -90 < theta < 90:
                points.append(_unit_sphere_point(theta, phi + dphi))
            points += [_unit_sphere_point(theta + dtheta, phi + dphi), _unit_sphere_point(theta + dtheta, phi)]
            vi, vn = len(g.vertices) + 1, len(g.normals) + 1
            g.vertices += [_v(place(p)) for p in points]
            g.normals += [_v(p) for p in points]
            g.faces.append([[vi + k, vn + k] for k in range(4 if -90 < theta < 90 else 3)])
    g.reduce_vertices()
    return g


@dataclass
class LegacyObjExport:
    sphere_dt: int = 10
    sphere_dp: int = 10
    group_by_tag: bool = False
    group_by_color: bool = False
    groups: dict[str, ObjGroup] = field(default_factory=dict)

    def _group(self, scene: SceneIR, i: int) -> ObjGroup:
        name = ""
        if self.group_by_tag:
            name += scene.tags[int(scene.tag[i])]
        if self.group_by_color:
            r, g, b = (int(float(c) * 255) for c in scene.rgba[i, :3])
            name += f"#{r:02x}{g:02x}{b:02x}"
        name = name or "default"
        return self.groups.setdefault(name, ObjGroup(name))

    def add(self, scene: SceneIR, i: int) -> None:
        kind = K(int(scene.kind[i]))
        if kind not in LEGACY_KINDS:
            return  # markers, and the cylinders / v2 solids 1.5's OBJ writer never saw (the modern OBJ has them)
        target = self._group(scene, i)
        if kind == K.SPHERE:
            c = _point(scene, i, (0.5, 0.5, 0.5))
            edge = c - _point(scene, i, (0.5, 0.5, 0.0))
            target.add_group(_sphere(c, F32(np.sqrt(_square_length(edge))), self.sphere_dt, self.sphere_dp))
            return
        target.add_group(_primitive(scene, i, kind))

    def lines(self) -> Iterator[str]:
        nv = nn = 0
        for name in sorted(self.groups):  # QMap iterates in key order
            g = self.groups[name]
            yield f"g {name}\nusemtl {name}\n"
            yield "".join(f"v {qnum(x)} {qnum(y)} {qnum(z)} \n" for x, y, z in g.vertices)
            yield "".join(f"vn {qnum(x)} {qnum(y)} {qnum(z)} \n" for x, y, z in g.normals)
            yield "".join(_face(face, nv, nn) for face in g.faces)
            nv, nn = nv + len(g.vertices), nn + len(g.normals)

    def render(self, scene: SceneIR) -> str:
        for i in range(len(scene)):
            self.add(scene, i)
        return "".join(self.lines())


def _face(face: list[list[int]], nv: int, nn: int) -> str:
    tag = "p " if len(face) == 1 else ("l " if len(face) == 2 else "f ")
    parts = [f"{v + nv} " if n == NO_NORMAL else f"{v + nv}//{n + nn} " for v, n in face]
    return tag + "".join(parts) + "\n"


def _primitive(scene: SceneIR, i: int, kind: K) -> ObjGroup:
    g = ObjGroup()
    base, d1, d2, d3 = legacy_vectors(scene.xform[i])
    if kind in (K.BOX, K.GRID):
        for quad in _box_faces(base, d1, d2, d3):
            (_quad if kind == K.BOX else _line_quad)(g, *quad)
        g.reduce_vertices()
    elif kind == K.MESH:
        for quad in _mesh_faces(scene.aux_data[scene.aux[i]].astype(F32), base, d1, d2):
            _quad(g, *quad)
        g.reduce_vertices()
    elif kind == K.LINE:
        g.vertices += [_v(_point(scene, i, (0.0, 0.5, 0.5))), _v(_point(scene, i, (1.0, 0.5, 0.5)))]
        g.faces.append([[1, NO_NORMAL], [2, NO_NORMAL]])
    elif kind == K.DOT:
        g.vertices.append(_v(_point(scene, i, (0.5, 0.5, 0.5))))
        g.faces.append([[1, NO_NORMAL]])
    elif kind == K.TRIANGLE:
        p = scene.aux_data[scene.aux[i], :9].astype(F32).reshape(3, 3)
        g.vertices += [_v(p[0]), _v(p[1]), _v(p[2])]
        g.faces.append([[1, NO_NORMAL], [2, NO_NORMAL], [3, NO_NORMAL]])
    return g
