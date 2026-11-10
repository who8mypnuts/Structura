"""PyMeshLab in the export pipeline (PLAN Q4): mesh clean-up before a mesh is written, and mesh checks.

A TriMesh goes into a PyMeshLab MeshSet with its vertex colours and, as the face quality, the SceneIR row each
triangle came from (so grouping by tag or material still works afterwards). Clean-up presets chain MeshLab
filters:

  clean        weld coincident vertices, drop duplicate and degenerate faces
  print-ready  clean, repair non-manifold edges and vertices, close holes, orient faces coherently
  light        clean, then quadric edge-collapse decimation to a share of the triangles
  smooth       clean, then Taubin smoothing (no shrinking)
  remesh       clean, then isotropic remeshing (even triangles)

PyMeshLab is imported only when a clean-up or check runs: start-up stays fast, and the GPL library is loaded
only on demand. Filters are looked up by name, so a renamed filter fails with a clear message.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np

from ...core.geometry.trimesh import TriMesh
from ...core.params import ParamSpec, ParamType

WELD = 0.001  # % of the bounding-box diagonal: vertices closer than this are one
Step = Callable[[Any, Any, float], None]  # (pymeshlab module, MeshSet, decimation share)


def _weld(ml: Any, ms: Any, _keep: float) -> None:
    _run(ms, "meshing_merge_close_vertices", threshold=ml.PercentageValue(WELD))
    for name in ("meshing_remove_duplicate_faces", "meshing_remove_null_faces", "meshing_remove_unreferenced_vertices"):
        _run(ms, name)


def _repair(_ml: Any, ms: Any, _keep: float) -> None:
    _run(ms, "meshing_repair_non_manifold_edges")
    _run(ms, "meshing_repair_non_manifold_vertices")
    _run(ms, "meshing_close_holes", maxholesize=1000)
    _run(ms, "meshing_re_orient_faces_coherently")


def _decimate(_ml: Any, ms: Any, keep: float) -> None:
    _run(ms, "meshing_decimation_quadric_edge_collapse", targetperc=keep, preservenormal=True, autoclean=True)


def _smooth(_ml: Any, ms: Any, _keep: float) -> None:
    _run(ms, "apply_coord_taubin_smoothing", stepsmoothnum=10)


def _remesh(ml: Any, ms: Any, _keep: float) -> None:
    _run(ms, "meshing_isotropic_explicit_remeshing", iterations=5, targetlen=ml.PercentageValue(1.0))


CLEANUPS: dict[str, tuple[Step, ...]] = {
    "none": (),
    "clean": (_weld,),
    "print-ready": (_weld, _repair),
    "light": (_weld, _decimate),
    "smooth": (_weld, _smooth),
    "remesh": (_weld, _remesh),
}
MESHLAB_OPTIONS = (
    ParamSpec("cleanup", ParamType.ENUM, "none", "Mesh clean-up (MeshLab)", choices=tuple(CLEANUPS),
              doc="clean: weld and dedupe · print-ready: also repair, close holes, orient · light: decimate · "
                  "smooth: Taubin · remesh: isotropic"),
    ParamSpec("keep", ParamType.FLOAT, 0.5, "Decimation: share of triangles kept", range=(0.01, 1.0)),
)  # fmt: skip


class MeshLabUnavailableError(RuntimeError):
    """PyMeshLab cannot be imported (not installed, or a system library it needs is missing)."""


def _pymeshlab() -> Any:
    try:
        import pymeshlab  # noqa: PLC0415 - heavy, and only needed when a clean-up or check runs
    except (ImportError, OSError) as exc:  # Linux wheels need libOpenGL.so.0 (package libopengl0)
        hint = " (on Linux install libopengl0)" if "libOpenGL" in str(exc) else ""
        raise MeshLabUnavailableError(f"PyMeshLab is unavailable: {exc}{hint}") from exc
    return pymeshlab


def _run(ms: Any, name: str, **kwargs: Any) -> Any:
    filter_ = getattr(ms, name, None)
    if filter_ is None:
        raise RuntimeError(f"this PyMeshLab has no filter '{name}' (PyMeshLab 2025.7 or newer is required)")
    return filter_(**kwargs)


def to_meshset(mesh: TriMesh) -> tuple[Any, Any]:
    """(pymeshlab, MeshSet) holding ``mesh`` with its colours and the owner row of every face."""
    ml = _pymeshlab()
    m = ml.Mesh(vertex_matrix=mesh.positions.astype(np.float64), face_matrix=mesh.indices.astype(np.int32),
                v_color_matrix=np.clip(mesh.colors, 0.0, 1.0).astype(np.float64),
                f_scalar_array=mesh.owners.astype(np.float64))  # fmt: skip
    ms = ml.MeshSet()
    ms.add_mesh(m, "structura")
    return ml, ms


def from_meshset(ms: Any) -> TriMesh:
    _run(ms, "compute_normal_per_vertex")
    m = ms.current_mesh()
    faces = m.face_number()
    owners = np.rint(m.face_scalar_array()).astype(np.int64) if m.has_face_scalar() else np.zeros(faces, np.int64)
    colors = m.vertex_color_matrix() if m.has_vertex_color() else np.ones((m.vertex_number(), 4))
    return TriMesh(m.vertex_matrix().astype(np.float32), m.vertex_normal_matrix().astype(np.float32),
                   colors.astype(np.float32), m.face_matrix().astype(np.uint32), np.maximum(owners, 0))  # fmt: skip


def clean_up(mesh: TriMesh, preset: str, keep: float = 0.5) -> TriMesh:
    """``mesh`` after the CLEANUPS ``preset`` ("none" returns it unchanged)."""
    steps = CLEANUPS[preset]
    if not steps or not mesh.triangles:
        return mesh
    ml, ms = to_meshset(mesh)
    for step in steps:
        step(ml, ms, keep)
    return from_meshset(ms)


@dataclass(frozen=True)
class MeshCheck:
    vertices: int
    triangles: int
    components: int
    boundary_edges: int
    holes: int
    non_manifold_edges: int
    non_manifold_vertices: int
    genus: int
    watertight: bool  # closed and two-manifold: a 3D printer can slice it
    area: float
    volume: float | None  # only meaningful when watertight

    def rows(self) -> list[tuple[str, str]]:
        """(label, value) for reports and the Check Mesh dialog."""
        volume = "—" if self.volume is None else f"{self.volume:.6g}"
        return [("Vertices", f"{self.vertices:,}"), ("Triangles", f"{self.triangles:,}"),
                ("Connected parts", f"{self.components:,}"), ("Watertight", "yes" if self.watertight else "no"),
                ("Holes", f"{self.holes:,}"), ("Boundary edges", f"{self.boundary_edges:,}"),
                ("Non-manifold edges", f"{self.non_manifold_edges:,}"),
                ("Non-manifold vertices", f"{self.non_manifold_vertices:,}"), ("Genus", str(self.genus)),
                ("Surface area", f"{self.area:.6g}"), ("Volume", volume)]  # fmt: skip


def check_mesh(mesh: TriMesh, weld: bool = True) -> MeshCheck:
    """MeshLab's topological and geometric measures of ``mesh`` (welded first: tessellated instances share no
    vertices, so unwelded every box would count as open)."""
    ml, ms = to_meshset(mesh)
    if weld:
        _weld(ml, ms, 1.0)
    topo = _run(ms, "get_topological_measures")
    geo = _run(ms, "get_geometric_measures")
    watertight = bool(topo["is_mesh_two_manifold"]) and int(topo["boundary_edges"]) == 0
    volume = geo.get("mesh_volume")
    return MeshCheck(
        int(topo["vertices_number"]), int(topo["faces_number"]), int(topo["connected_components_number"]),
        int(topo["boundary_edges"]), max(0, int(topo.get("number_holes", 0))), int(topo["non_two_manifold_edges"]),
        int(topo["non_two_manifold_vertices"]), int(topo.get("genus", 0)), watertight,
        float(geo.get("surface_area", 0.0)), float(volume) if watertight and volume is not None else None,
    )  # fmt: skip
