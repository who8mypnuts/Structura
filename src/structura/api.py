"""Structura's Python API (docs/16 §4): build, render and export scripts without the GUI.

import structura as st
scene = st.build("spiral.es", seed=3)
st.render(scene, "spiral.png", samples=128, integrator="path")
st.export(scene, "spiral.usdz")

doc = st.open("tree.structura")               # a script or a project: text, seed, parameters, camera, timeline
doc.params["angle"] = 30
st.render(doc.build(), "tree.png", camera=doc.camera)
for frame, scene in doc.animate():            # the project's timeline (v2 scripts: 'time', 'frame', 'fps')
    st.render(scene, f"tree_{frame:04d}.png", camera=doc.camera_at(frame), samples=32)
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from .compute.select import select_backend
from .core.animation.camera import camera_at, has_camera_tracks
from .core.animation.timeline import Timeline
from .core.build.api import build_scene
from .core.lang.api import compile_script
from .core.lang.source import detect_dialect
from .core.project.model import SUFFIX
from .core.project.model import load as load_project
from .core.scene.camera import Camera
from .core.scene.ir import SceneIR
from .core.scene.lens import Lens
from .core.text_file import read_script
from .export.api import export_scene
from .export.base import ExportReport
from .render.animation import Animation, build_frame
from .render.api import RenderProgress, prepare_with_frame, progressive, script_settings
from .render.metadata import render_metadata
from .render.output import save_image


@dataclass
class Document:
    """A script or project, opened for building (docs/16 §4): change ``params`` or ``seed``, then build."""

    text: str
    path: Path | None = None
    seed: int = 0
    params: dict[str, float] = field(default_factory=dict)
    camera: Camera | None = None  # the project's camera (None: the script's, or framing)
    timeline: Timeline = field(default_factory=Timeline)
    render_overrides: dict[str, Any] = field(default_factory=dict)

    @property
    def dialect(self) -> int:
        return detect_dialect(self.text)

    def animation(self) -> Animation:
        folder = self.path.parent if self.path else None
        return Animation(self.text, self.timeline, self.seed, dict(self.params), folder, self.camera,
                         self.render_overrides)  # fmt: skip

    def build(self, seed: int | None = None, frame: int = 0) -> SceneIR:
        folder = self.path.parent if self.path else None
        used = self.seed if seed is None else seed
        compiled = compile_script(self.text, used, self.params, folder, frame, self.timeline.fps)
        return build_scene(compiled.program, used).scene

    def animate(self, frames: Iterable[int] | None = None) -> Iterator[tuple[int, SceneIR]]:
        """(frame, scene) for each frame (default: the timeline's range), with its keyed parameters and seed."""
        anim = self.animation()
        for frame in anim.frames() if frames is None else frames:
            yield frame, build_frame(anim, frame)[0]

    def camera_at(self, frame: int) -> Camera | None:
        """The camera at ``frame``: the project camera moved by the timeline's camera tracks."""
        if self.camera is None or not has_camera_tracks(self.timeline):
            return self.camera
        return camera_at(self.timeline, frame, self.camera)


def open(path: str | Path) -> Document:
    """Open an .es script or a .structura project."""
    path = Path(path)
    if path.suffix.lower() == SUFFIX:
        project = load_project(path)
        return Document(project.text, path, project.seed, dict(project.params), project.camera,
                        project.timeline or Timeline(), dict(project.render))  # fmt: skip
    return Document(read_script(path), path)


def build(
    script: str | Path,
    seed: int = 0,
    params: dict[str, float] | None = None,
    frame: int = 0,
    fps: float = 24.0,
) -> SceneIR:
    """Build a script (a path, or EisenScript text) into a scene."""
    path = Path(script) if not isinstance(script, str) or ("\n" not in script and Path(script).exists()) else None
    text = read_script(path) if path else str(script)
    compiled = compile_script(text, seed, params, path.parent if path else None, frame, fps)
    return build_scene(compiled.program, seed).scene


def render(
    scene: SceneIR,
    output: str | Path | None = None,
    device: str = "auto",
    camera: Camera | None = None,
    lens: Lens | None = None,
    **settings: Any,
) -> RenderProgress:
    """Render ``scene`` (script settings, then ``settings`` overrides such as samples=, integrator=, width=).
    ``camera`` replaces the script's camera; ``lens`` replaces its lens (``Lens(fstop=2.8)`` …); ``post=`` a
    render.post look (``LOOKS["Neon"]``, ``PostSettings(bloom=0.1)``) finishes the saved image."""
    config = replace(script_settings(scene), **settings)
    prepared, frame = prepare_with_frame(scene, config, camera=camera)
    if lens is not None:
        frame = replace(frame, camera=replace(frame.camera, lens=lens))
    *_, result = progressive(prepared, config, select_backend(device), frame)
    if output is not None:
        save_image(result.image, Path(output), config.display, render_metadata(config, frame.camera))
    return result


def export(scene: SceneIR, output: str | Path, format: str | None = None, **options: Any) -> ExportReport:
    """Export ``scene``; the extension picks the format unless ``format`` names an exporter."""
    return export_scene(scene, Path(output), format, options)


__all__ = ["Camera", "Document", "Lens", "build", "export", "open", "render"]
