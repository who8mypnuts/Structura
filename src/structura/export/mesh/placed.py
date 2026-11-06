"""Prototype + Transform scene graphs for X3D and VRML97 (docs/15 §3): every affine-placeable instance becomes a
Transform (exact, shear included, through scaleOrientation) that USEs its prototype's geometry and its
colour's appearance; the other kinds are baked into one vertex-coloured mesh."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import numpy as np

from ...core.geometry.affine import scaled_transforms
from ...core.geometry.tessellate import TessOptions, tessellate
from ...core.geometry.trimesh import TriMesh
from ..affine_instances import AffineGroup, affine_groups
from ..base import ExportJob


def floats(a: np.ndarray) -> str:
    return " ".join(f"{v:.6g}" for v in np.asarray(a, np.float64).ravel().tolist())


@dataclass(frozen=True)
class Placement:
    group: AffineGroup
    row: int  # SceneIR row
    fields: dict[str, str]  # translation, rotation, scale, scaleOrientation
    rgba: np.ndarray


@dataclass(frozen=True)
class PlacedScene:
    placements: list[Placement]
    rest: TriMesh  # baked kinds, in output axes
    rest_points: np.ndarray
    rest_normals: np.ndarray


def placed_scene(job: ExportJob, lod: str) -> PlacedScene:
    groups, covered = affine_groups(job, lod)
    placements = []
    for group in groups:
        t = scaled_transforms(group.matrices)
        for i, row in enumerate(group.rows.tolist()):
            fields = {"translation": floats(t.translation[i]), "rotation": floats(t.rotation[i]),
                      "scale": floats(t.scale[i]), "scaleOrientation": floats(t.scale_orientation[i])}  # fmt: skip
            placements.append(Placement(group, row, fields, job.scene.rgba[row]))
    rest = tessellate(job.scene.subset(np.nonzero(~covered)[0]), TessOptions(lod=lod))
    return PlacedScene(placements, rest, job.model.points(rest.positions), job.model.directions(rest.normals))


def colour_key(rgba: np.ndarray) -> str:
    q = np.clip(np.rint(np.asarray(rgba) * 255), 0, 255).astype(int).tolist()
    return "c{:02x}{:02x}{:02x}{:02x}".format(*q)


def first_uses(keys: list[str]) -> Iterator[tuple[str, bool]]:
    """(key, defined here) — the first occurrence of a key DEFines it, later ones USE it."""
    seen: set[str] = set()
    for key in keys:
        yield key, key not in seen
        seen.add(key)
