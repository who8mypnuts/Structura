"""Animation frames (docs/16 §2.3): one script evaluated at a timeline frame, built and rendered.

Shared by `structura animate`, the GUI's Render Animation job and the Python API, so every path applies the
timeline the same way: keyed parameters and seed first, then the v2 'frame' / 'time' / 'fps' variables, then
the camera tracks.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from ..compute.base import Backend
from ..core.animation.camera import camera_at, has_camera_tracks
from ..core.animation.paths import Turntable, turntable
from ..core.animation.timeline import Timeline
from ..core.build.api import build_scene
from ..core.lang.api import compile_script
from ..core.scene.camera import Camera
from ..core.scene.ir import SceneIR
from .api import RenderProgress, prepare_with_frame, progressive, script_settings
from .settings import RenderSettings


@dataclass(frozen=True)
class Animation:
    text: str
    timeline: Timeline = field(default_factory=Timeline)
    seed: int = 0
    params: Mapping[str, float] = field(default_factory=dict)
    script_dir: Path | None = None
    camera: Camera | None = None  # the base camera (None: the script's, or framing)
    overrides: Mapping[str, Any] = field(default_factory=dict)  # RenderSettings fields

    def frames(self) -> range:
        return range(self.timeline.start, self.timeline.end + 1)


def frame_path(pattern: Path, frame: int) -> Path:
    """'frames/out.png' → 'frames/out_0012.png'."""
    return pattern.with_name(f"{pattern.stem}_{frame:04d}{pattern.suffix}")


def build_frame(anim: Animation, frame: int) -> tuple[SceneIR, int]:
    """(the scene at ``frame``, the seed used)."""
    seed_value = anim.timeline.value("seed", frame)
    seed = anim.seed if seed_value is None else int(seed_value)
    params = {**anim.params, **anim.timeline.params_at(frame)}
    compiled = compile_script(anim.text, seed, params, anim.script_dir, frame, anim.timeline.fps)
    return build_scene(compiled.program, seed).scene, seed


def frame_settings(anim: Animation, scene: SceneIR) -> RenderSettings:
    return replace(script_settings(scene), **anim.overrides)


def render_frame(
    anim: Animation, frame: int, backend: Backend, between: Callable[[], None] | None = None
) -> tuple[RenderProgress, RenderSettings]:
    """Build and render ``frame``; the camera is the base camera (or the script's) moved by the camera tracks."""
    scene, _ = build_frame(anim, frame)
    settings = frame_settings(anim, scene)
    prepared, view = prepare_with_frame(scene, settings, camera=anim.camera)
    if has_camera_tracks(anim.timeline):
        view = replace(view, camera=camera_at(anim.timeline, frame, view.camera))
    *_, result = progressive(prepared, settings, backend, view, between)
    return result, settings


def with_turntable(anim: Animation, spec: Turntable) -> Animation:
    """``anim`` orbiting its first frame's camera (the base camera, else the script's or the framing one)."""
    scene, _ = build_frame(anim, spec.start)
    _, view = prepare_with_frame(scene, frame_settings(anim, scene), camera=anim.camera)
    return replace(anim, timeline=turntable(anim.timeline, view.camera, spec), camera=view.camera)
