"""The project model and its JSON form (docs/07 §8). Qt-free. A project is a script (embedded, or linked to
an .es file next to it) plus the state the script does not hold: seed, parameter values, camera, render
overrides, the animation timeline and a thumbnail. Later milestones fill the reserved sections (materials,
lights …)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ... import __version__
from ..animation.timeline import Timeline
from ..animation.timeline import from_dict as timeline_from
from ..animation.timeline import to_dict as timeline_dict
from ..scene.camera import Camera
from ..text_file import read_script
from .migrations import CURRENT_VERSION, migrate

FORMAT = "structura-project"
SUFFIX = ".structura"
RESERVED = ("materials", "lights", "environment", "export_presets")


@dataclass(frozen=True)
class Project:
    text: str  # the script
    linked: str | None = None  # path of the linked .es file, relative to the project; None = embedded
    seed: int = 0
    auto_increment_seed: bool = False
    params: dict[str, float] = field(default_factory=dict)
    camera: Camera | None = None
    camera_lock_to_script: bool = False
    render: dict[str, Any] = field(default_factory=dict)  # Render Settings overrides
    thumbnail_png_b64: str = ""
    timeline: Timeline | None = None  # keyframes (docs/16 §2); None: no animation
    reserved: dict[str, Any] = field(default_factory=dict)  # sections this version keeps but does not edit


def _camera_json(camera: Camera | None) -> dict[str, Any] | None:
    return None if camera is None else {"kind": "perspective", **asdict(camera)}


def _vec3(value: Any, default: tuple[float, float, float]) -> tuple[float, float, float]:
    if isinstance(value, list | tuple) and len(value) == 3:
        return (float(value[0]), float(value[1]), float(value[2]))
    return default


def _camera(data: Any) -> Camera | None:
    if not isinstance(data, dict) or "eye" not in data or "target" not in data:
        return None
    focus = data.get("focus_distance")
    return Camera(
        eye=_vec3(data["eye"], (0.0, 0.0, 10.0)), target=_vec3(data["target"], (0.0, 0.0, 0.0)),
        up=_vec3(data.get("up"), (0.0, 1.0, 0.0)), fov_y_deg=float(data.get("fov_y_deg", 22.0)),
        aperture_radius=float(data.get("aperture_radius", 0.0)),
        focus_distance=None if focus is None else float(focus),
    )  # fmt: skip


def to_json(project: Project, dialect: int = 1) -> str:
    script: dict[str, Any] = {"mode": "linked", "path": project.linked} if project.linked else {"mode": "embedded"}
    if not project.linked:
        script["text"] = project.text
    data = {
        "format": FORMAT, "format_version": CURRENT_VERSION, "app_version": __version__,
        "script": script | {"dialect": dialect}, "seed": project.seed,
        "auto_increment_seed": project.auto_increment_seed, "params": project.params,
        "camera": _camera_json(project.camera), "camera_lock_to_script": project.camera_lock_to_script,
        "render": project.render, **project.reserved, "thumbnail_png_b64": project.thumbnail_png_b64,
    }  # fmt: skip
    if project.timeline is not None:
        data["timeline"] = timeline_dict(project.timeline)
    return json.dumps(data, indent=2) + "\n"


def from_json(text: str, base: Path) -> Project:
    """Parse a project; a linked script is read relative to ``base`` (the project's folder)."""
    data = json.loads(text)
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise ValueError("not a Structura project")
    data = migrate(data)
    script = data.get("script") or {}
    linked = script.get("path") if script.get("mode") == "linked" else None
    source = read_script(base / linked) if linked else str(script.get("text", ""))
    return Project(
        text=source, linked=linked, seed=int(data.get("seed", 0)),
        auto_increment_seed=bool(data.get("auto_increment_seed", False)),
        params={str(k): float(v) for k, v in (data.get("params") or {}).items()},
        camera=_camera(data.get("camera")), camera_lock_to_script=bool(data.get("camera_lock_to_script", False)),
        render=dict(data.get("render") or {}), thumbnail_png_b64=str(data.get("thumbnail_png_b64", "")),
        timeline=timeline_from(data["timeline"]) if data.get("timeline") else None,
        reserved={k: data[k] for k in RESERVED if k in data},
    )  # fmt: skip


def load(path: Path) -> Project:
    return from_json(path.read_text(encoding="utf-8"), path.parent)


def save(path: Path, project: Project, dialect: int = 1) -> None:
    """Write the project file. A linked script is not written here: its editor tab saves the .es file."""
    path.write_text(to_json(project, dialect), encoding="utf-8")
