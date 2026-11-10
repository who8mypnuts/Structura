"""Structure Synth's CSG markers evaluated as solids (docs/15 §3.1): 'template::union-begin' … '-end', and the
same for 'difference' and 'intersection', in emission order. The 1.5 "CSG test" example becomes printable
without POV-Ray. Primitives outside any group are kept as they are; a group's first operand is the one the
rest are subtracted from."""

from __future__ import annotations

from dataclasses import dataclass, field

import manifold3d as mf
import numpy as np

from ..core.geometry.tessellate import TessOptions, tessellate
from ..core.geometry.trimesh import TriMesh
from ..core.params import ParamSpec, ParamType
from ..core.scene.ir import PrimitiveKind as K
from ..core.scene.ir import SceneIR
from .base import ExportJob
from .mesh.meshlab import clean_up
from .solids import as_trimesh, instance_solids, triangles, union

OPERATIONS = ("union", "difference", "intersection")


@dataclass
class Group:
    op: str
    items: list[int | Group] = field(default_factory=list)  # SceneIR rows and nested groups


def csg_tree(scene: SceneIR) -> tuple[Group, list[str]]:
    """The marker structure as nested groups (the root is a plain union of its items), and warnings."""
    root, stack, warnings = Group("root"), [], []
    current = root
    for row in range(len(scene)):
        if scene.kind[row] != K.TEMPLATE:
            current.items.append(row)
            continue
        op, _, edge = scene.tags[scene.tag[row]].rpartition("-")
        if op not in OPERATIONS or edge not in ("begin", "end"):
            continue
        if edge == "begin":
            stack.append(current)
            current = Group(op)
        elif current.op == op:
            done, current = current, stack.pop()
            current.items.append(done)
        else:
            warnings.append(f"'{op}-end' does not close '{current.op}-begin': ignored")
    if stack:
        warnings.append(f"{len(stack)} CSG group(s) never closed: closed at the end")
        while stack:
            done, current = current, stack.pop()
            current.items.append(done)
    return root, warnings


def has_markers(scene: SceneIR) -> bool:
    kinds = scene.kind == K.TEMPLATE
    return bool(kinds.any()) and any(scene.tags[t].startswith(OPERATIONS) for t in np.unique(scene.tag[kinds]))


def _evaluate(group: Group, solids: dict[int, mf.Manifold]) -> mf.Manifold:
    operands = [_evaluate(i, solids) if isinstance(i, Group) else solids.get(i) for i in group.items]
    present = [m for m in operands if m is not None and not m.is_empty()]
    if not present:
        return mf.Manifold()
    if group.op == "difference":
        return present[0] - union(present[1:]) if len(present) > 1 else present[0]
    if group.op == "intersection":
        result = present[0]
        for m in present[1:]:
            result = result ^ m
        return result
    return union(present)


def csg_mesh(scene: SceneIR, lod: str = "medium") -> tuple[TriMesh, list[str]]:
    """The scene with every CSG group evaluated; primitives outside groups pass through unchanged."""
    root, warnings = csg_tree(scene)
    mesh = tessellate(scene, TessOptions(lod=lod))
    grouped = [i for i in root.items if isinstance(i, Group)]
    loose = np.array([i for i in root.items if not isinstance(i, Group)], np.int64)
    solids = instance_solids(mesh)
    parts = [_subset(mesh, loose)]
    for group in grouped:
        corners, colours = triangles(_evaluate(group, solids))
        parts.append(as_trimesh(corners, colours))
    return TriMesh.concat(parts), warnings


def _subset(mesh: TriMesh, rows: np.ndarray) -> TriMesh:
    return mesh.select(np.isin(mesh.owners, rows))


CSG_OPTION = ParamSpec("csg", ParamType.BOOL, False, "Evaluate CSG markers (template::union-begin …)")


def export_mesh(job: ExportJob) -> tuple[TriMesh, tuple[str, ...]]:
    """The triangles a mesh exporter writes: CSG groups evaluated when asked for, else plain tessellation;
    then the MeshLab clean-up the options name (mesh/meshlab.py)."""
    lod = job.options["lod"]
    warnings: list[str] = []
    if job.options.get("csg") and has_markers(job.scene):
        mesh, warnings = csg_mesh(job.scene, lod)
    else:
        mesh = tessellate(job.scene, TessOptions(lod=lod))
    cleanup = str(job.options.get("cleanup", "none"))
    if cleanup != "none":
        job.progress(0.0, f"MeshLab clean-up ({cleanup}) of {mesh.triangles:,} triangles")
        mesh = clean_up(mesh, cleanup, float(job.options.get("keep", 0.5)))
    return mesh, tuple(warnings)
