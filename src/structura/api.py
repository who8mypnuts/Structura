"""Structura's Python API (docs/16 §4): build, render and export scripts without the GUI.

import structura.api as st
scene = st.build("spiral.es", seed=3)
st.render(scene, "spiral.png", samples=128, integrator="path")
st.export(scene, "spiral.usdz")
for frame in range(48):                       # v2 scripts can use 'time', 'frame' and 'fps'
    st.render(st.build("anim.es", frame=frame), f"anim_{frame:04d}.png", samples=32)
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from .compute.select import select_backend
from .core.build.api import build_scene
from .core.lang.api import compile_script
from .core.scene.camera import Camera
from .core.scene.ir import SceneIR
from .export.api import export_scene
from .export.base import ExportReport
from .render.api import RenderProgress, prepare, progressive, script_settings
from .render.config import scene_frame
from .render.metadata import render_metadata
from .render.output import save_image


def build(
    script: str | Path,
    seed: int = 0,
    params: dict[str, float] | None = None,
    frame: int = 0,
    fps: float = 24.0,
) -> SceneIR:
    """Build a script (a path, or EisenScript text) into a scene."""
    path = Path(script) if not isinstance(script, str) or ("\n" not in script and Path(script).exists()) else None
    text = path.read_text(encoding="utf-8") if path else str(script)
    compiled = compile_script(text, seed, params, path.parent if path else None, frame, fps)
    return build_scene(compiled.program, seed).scene


def render(
    scene: SceneIR,
    output: str | Path | None = None,
    device: str = "auto",
    camera: Camera | None = None,
    **settings: Any,
) -> RenderProgress:
    """Render ``scene`` (script settings, then ``settings`` overrides such as samples=, integrator=, width=)."""
    config = replace(script_settings(scene), **settings)
    prepared = prepare(scene)
    frame = scene_frame(prepared.scene_settings, config, prepared.lo, prepared.hi, prepared.declarations)
    if camera is not None:
        frame = replace(frame, camera=camera)
    *_, result = progressive(prepared, config, select_backend(device), frame)
    if output is not None:
        save_image(result.image, Path(output), 0.0, config.view_transform, render_metadata(config, frame.camera))
    return result


def export(scene: SceneIR, output: str | Path, format: str | None = None, **options: Any) -> ExportReport:
    """Export ``scene``; the extension picks the format unless ``format`` names an exporter."""
    return export_scene(scene, Path(output), format, options)


__all__ = ["build", "export", "render"]
