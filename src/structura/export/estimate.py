"""File-size estimate for the export sheet (docs/14 §5.5 "a live estimate of prims and file size").

Formats differ too much for a formula, so two small samples of the scene are exported for real and the size is
extrapolated linearly: size(n) ≈ a + b·n. The samples keep the scene's mix of primitive kinds and its extent.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from ..core.scene.camera import Camera
from ..core.scene.ir import SceneIR
from .api import export_scene

SAMPLE = 400


def _sample(scene: SceneIR, count: int) -> SceneIR:
    rows = np.unique(np.linspace(0, len(scene) - 1, min(count, len(scene))).round().astype(np.int64))
    return scene.subset(rows)


def _size(scene: SceneIR, name: str, suffix: str, options: dict[str, Any], camera: Camera | None) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / f"sample{suffix}"
        report = export_scene(scene, target, name, options, camera)
        files = set(report.files) | {target}
        return sum(p.stat().st_size for p in files if p.exists())


def estimate_size(scene: SceneIR, name: str, suffix: str, options: dict[str, Any], camera: Camera | None = None) -> int:
    """Estimated bytes of exporting ``scene`` with exporter ``name`` (the sidecar files included)."""
    if len(scene) <= SAMPLE:
        return _size(scene, name, suffix, options, camera)
    small, large = SAMPLE // 2, SAMPLE
    s_small = _size(_sample(scene, small), name, suffix, options, camera)
    s_large = _size(_sample(scene, large), name, suffix, options, camera)
    per_object = max(0.0, (s_large - s_small) / (large - small))
    return int(max(s_large, s_large + per_object * (len(scene) - large)))


def human(size: int) -> str:
    for unit in ("bytes", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:,.0f} {unit}" if unit == "bytes" else f"{size:,.1f} {unit}"
        size /= 1024  # type: ignore[assignment]
    return f"{size} bytes"
