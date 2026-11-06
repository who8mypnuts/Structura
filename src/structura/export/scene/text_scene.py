"""The context of the text scene writers (docs/15 §4.4): POV-Ray 3.8, Sunflow and Mitsuba 3 share one model —
unit prototypes placed by full affine matrices, one shader per (material, colour), the baked remainder, the
camera and a sun — and each target is a Jinja2 template (export/scene/text/*.j2)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import jinja2
import numpy as np

from ...core.color import srgb_to_linear
from ...core.geometry.tessellate import TessOptions, tessellate
from ...core.geometry.trimesh import TriMesh
from ...core.scene.material import Material
from ..affine_instances import AffineGroup, Prototype, affine_groups
from ..base import ExportJob

TEMPLATES = Path(__file__).resolve().parent / "text"
SUN = (0.35, 0.8, 0.5)  # towards the sun, when the script declares none (Structura's default key light)


def num(value: float) -> str:
    return f"{float(value):.6g}"


def vec(values: Any) -> str:
    return " ".join(num(v) for v in np.asarray(values, np.float64).ravel().tolist())


def csv(values: Any) -> str:
    return ", ".join(num(v) for v in np.asarray(values, np.float64).ravel().tolist())


@cache
def environment() -> jinja2.Environment:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATES), autoescape=False, keep_trailing_newline=True,
                             trim_blocks=True, lstrip_blocks=True, undefined=jinja2.StrictUndefined)  # fmt: skip
    env.filters.update(num=num, vec=vec, csv=csv, ident=lambda key: str(key).replace("-", "_").replace(".", "_"))
    return env


@dataclass(frozen=True)
class Shader:
    name: str
    material: Material
    rgba: tuple[float, float, float, float]  # sRGB colour (the instance's, or the material's own base)

    @property
    def linear(self) -> tuple[float, float, float]:
        r, g, b = (float(v) for v in srgb_to_linear(np.asarray(self.rgba[:3], np.float32)))
        return (r, g, b)

    @property
    def kind(self) -> str:
        """The closest classic shader: glass, mirror, shiny, emissive or diffuse."""
        m = self.material
        if m.emission_strength > 0:
            return "emissive"
        if m.transmission > 0.5:
            return "glass"
        if m.metallic > 0.5 and m.roughness < 0.15:
            return "mirror"
        return "shiny" if m.roughness < 0.35 or m.coat > 0.5 else "diffuse"


@dataclass(frozen=True)
class Placed:
    proto: Prototype
    matrix: np.ndarray  # float64[3, 4] unit cube → output
    shader: str

    @property
    def rows4(self) -> np.ndarray:
        """Row-major 4×4 (column-vector convention)."""
        return np.vstack([self.matrix, [0.0, 0.0, 0.0, 1.0]])

    @property
    def pov(self) -> np.ndarray:
        """POV-Ray's 'matrix <…>' (row-vector convention): Lᵀ then the translation."""
        return np.vstack([self.matrix[:, :3].T, self.matrix[:, 3]])


class _Shaders:
    """One shader per (material, colour); instances with a material of their own colour share it."""

    def __init__(self, job: ExportJob) -> None:
        self.job = job
        self.by_key: dict[tuple[str, tuple[float, ...]], Shader] = {}
        table = job.model.materials
        self.mat_of_row = table.by_tag[job.scene.tag] if len(job.scene) else np.zeros(0, np.int32)

    def for_row(self, row: int) -> str:
        table = self.job.model.materials
        material = table.materials[int(self.mat_of_row[row])] if len(table) else Material()
        if material.uses_state_color:
            rgba = tuple(float(v) for v in self.job.scene.rgba[row])
        else:
            rgba = (*(float(v) for v in material.base), 1.0)
        key = (material.name, tuple(round(v, 4) for v in rgba))
        if key not in self.by_key:
            r, g, b, a = rgba
            self.by_key[key] = Shader(f"s{len(self.by_key)}", material, (r, g, b, a))
        return self.by_key[key].name


def _camera(job: ExportJob) -> dict[str, Any]:
    cam, model = job.model.camera, job.model
    forward, right, up = (model.directions(v[None].astype(np.float32))[0] for v in cam.basis)
    half = math.tan(math.radians(cam.fov_y_deg) / 2)
    return {"eye": model.points(np.asarray(cam.eye, np.float32)[None])[0],
            "target": model.points(np.asarray(cam.target, np.float32)[None])[0], "up": up, "right": right,
            "forward": forward, "fov_y": cam.fov_y_deg, "aspect": model.aspect,
            "fov_x": math.degrees(2 * math.atan(half * model.aspect))}  # fmt: skip


def _sun(job: ExportJob) -> np.ndarray:
    decl = job.scene.declarations
    sun = next((light for light in decl.lights if light.type == "sun"), None) if decl else None
    travel = sun.values.get("direction") if sun else None
    d = -np.asarray(travel, np.float64) if isinstance(travel, tuple) else np.asarray(SUN)
    out: np.ndarray = job.model.directions((d / np.linalg.norm(d)).astype(np.float32)[None])[0]
    return out


def _rest(job: ExportJob, covered: np.ndarray, shaders: _Shaders, lod: str) -> dict[str, Any] | None:
    rows = np.nonzero(~covered)[0]
    mesh: TriMesh = tessellate(job.scene.subset(rows), TessOptions(lod=lod))
    if not mesh.triangles:
        return None
    names = [shaders.for_row(int(r)) for r in rows.tolist()]
    unique = sorted(set(names), key=names.index)
    face_shaders = np.array([unique.index(names[o]) for o in mesh.owners.tolist()], np.int64)
    return {"mesh": mesh, "points": job.model.points(mesh.positions), "normals": job.model.directions(mesh.normals),
            "triangles": mesh.indices, "colors": mesh.colors, "shader_names": unique,
            "face_shaders": face_shaders}  # fmt: skip


def text_scene(job: ExportJob, lod: str) -> dict[str, Any]:
    """The template context."""
    groups, covered = affine_groups(job, lod)
    shaders = _Shaders(job)
    placed = [Placed(g.proto, m.astype(np.float64), shaders.for_row(int(r)))
              for g in groups for r, m in zip(g.rows.tolist(), g.matrices, strict=True)]  # fmt: skip
    rest = _rest(job, covered, shaders, lod)
    background = np.asarray(job.model.background, np.float32)
    up = job.model.directions(np.array([[0, 1, 0]], np.float32))[0]
    east = job.model.directions(np.array([[0, 0, 1]], np.float32))[0]
    return {"camera": _camera(job), "background": background, "background_linear": srgb_to_linear(background),
            "sun": _sun(job), "up": up, "east": east,
            "prototypes": _prototypes(groups), "placed": placed, "shaders": list(shaders.by_key.values()),
            "rest": rest}  # fmt: skip


def _prototypes(groups: list[AffineGroup]) -> list[Prototype]:
    seen: dict[str, Prototype] = {}
    for g in groups:
        seen.setdefault(g.proto.key, g.proto)
    return list(seen.values())


def render_template(name: str, context: dict[str, Any]) -> str:
    return environment().get_template(name).render(**context)
