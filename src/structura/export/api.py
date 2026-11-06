"""Export entry point shared by the GUI (ExportService) and the CLI (docs/15 §7)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..core.params import resolve
from ..core.scene.camera import Camera
from ..core.scene.ir import SceneIR
from . import legacy as _legacy  # noqa: F401 - last: '.obj' defaults to the modern exporter
from .base import EXPORTERS, Exporter, ExportJob, ExportReport, exporter_for
from .mesh import obj as _obj  # noqa: F401 - registers exporters
from .mesh import ply as _ply  # noqa: F401
from .mesh import stl as _stl  # noqa: F401
from .mesh import threemf as _threemf  # noqa: F401
from .mesh import vrml as _vrml  # noqa: F401
from .mesh import x3d as _x3d  # noqa: F401
from .scene import blender as _blender  # noqa: F401
from .scene import gltf as _gltf  # noqa: F401
from .scene import usd as _usd  # noqa: F401
from .scene_model import scene_model


def find_exporter(path: Path, name: str | None = None) -> Exporter:
    exporter = EXPORTERS.get(name) if name else exporter_for(path)
    if exporter is None:
        known = ", ".join(sorted(EXPORTERS))
        raise ValueError(f"no exporter for '{path.suffix}'" if not name else f"unknown format '{name}' ({known})")
    return exporter


def export_scene(
    scene: SceneIR,
    path: Path,
    name: str | None = None,
    options: dict[str, Any] | None = None,
    camera: Camera | None = None,
    progress: Callable[[float, str], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> ExportReport:
    exporter = find_exporter(path, name)
    values = resolve(exporter.params, options)
    model = scene_model(scene, camera, values.get("up", "y"), values.get("unit_scale", 1.0))
    job = ExportJob(scene, model, values, progress or (lambda _f, _t: None), cancelled or (lambda: False))
    path.parent.mkdir(parents=True, exist_ok=True)
    return exporter.write(job, path)


__all__ = ["EXPORTERS", "ExportReport", "Exporter", "export_scene", "find_exporter"]
