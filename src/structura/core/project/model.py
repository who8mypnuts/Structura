"""The project model and its JSON form (docs/07 §8). Qt-free. A project is a script (embedded, or linked to
an .es file next to it) plus the state the script does not hold: seed, parameter values, camera, render
overrides, the animation timeline and a thumbnail. Later milestones fill the reserved sections (materials,
lights …)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from ... import __version__
from ..animation.timeline import Timeline
from ..animation.timeline import from_dict as timeline_from
from ..animation.timeline import to_dict as timeline_dict
from ..scene.camera import LEGACY_FOV, Camera
from ..scene.lens import Lens
from ..scene.vectors import vec3_of
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
    bookmarks: dict[str, Camera] = field(default_factory=dict)  # saved views (Camera panel)
    reserved: dict[str, Any] = field(default_factory=dict)  # sections this version keeps but does not edit


def camera_to_dict(camera: Camera | None) -> dict[str, Any] | None:
    """Returns the JSON form of a camera, or None without one.

    Args:
        camera: The camera; its 'kind' entry names the lens projection.
    """
    return None if camera is None else {"kind": camera.lens.projection, **asdict(camera)}


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def lens_from_dict(data: Any) -> Lens:
    """Reads a lens from its JSON form.

    Args:
        data: The 'lens' object of a camera; anything else gives the default lens.

    Returns:
        The lens; unknown keys are ignored and values that do not convert keep their defaults.
    """
    if not isinstance(data, dict):
        return Lens()
    values: dict[str, Any] = {}
    for f in fields(Lens):
        if f.name not in data:
            continue
        default, raw = getattr(Lens(), f.name), data[f.name]
        try:
            if isinstance(default, tuple):
                values[f.name] = (float(raw[0]), float(raw[1]))
            elif f.name in ("fstop", "focus_distance"):
                values[f.name] = None if raw is None else float(raw)
            else:
                values[f.name] = type(default)(raw)
        except (TypeError, ValueError, IndexError):
            continue
    return Lens(**values)


def camera_from_dict(data: Any) -> Camera | None:
    """Reads a camera from its JSON form.

    Format 1 projects (and renders made before the lens existed) kept 'aperture_radius' and 'focus_distance' on
    the camera itself; they move into the lens.

    Args:
        data: The 'camera' object.

    Returns:
        The camera, or None when ``data`` has no eye and target. Malformed vectors and numbers fall back to the
        defaults.
    """
    if not isinstance(data, dict) or "eye" not in data or "target" not in data:
        return None
    lens = dict(data.get("lens") or {})
    for old in ("aperture_radius", "focus_distance"):  # format 1 (and renders made before the lens)
        if old in data and old not in lens:
            lens[old] = data[old]
    if lens.get("focus_distance") is not None and "focus_mode" not in lens:
        lens["focus_mode"] = "manual"
    return Camera(
        eye=vec3_of(data["eye"], (0.0, 0.0, 10.0)), target=vec3_of(data["target"], (0.0, 0.0, 0.0)),
        up=vec3_of(data.get("up"), (0.0, 1.0, 0.0)), fov_y_deg=_float(data.get("fov_y_deg"), LEGACY_FOV),
        lens=lens_from_dict(lens),
    )  # fmt: skip


def to_json(project: Project, dialect: int = 1) -> str:
    """Serialises a project.

    Args:
        project: The project (an embedded or a linked script, and its state).
        dialect: The EisenScript dialect of its script (1 or 2), recorded for readers.

    Returns:
        The JSON text of the current format version.
    """
    script: dict[str, Any] = {"mode": "linked", "path": project.linked} if project.linked else {"mode": "embedded"}
    if not project.linked:
        script["text"] = project.text
    data = {
        "format": FORMAT, "format_version": CURRENT_VERSION, "app_version": __version__,
        "script": script | {"dialect": dialect}, "seed": project.seed,
        "auto_increment_seed": project.auto_increment_seed, "params": project.params,
        "camera": camera_to_dict(project.camera), "camera_lock_to_script": project.camera_lock_to_script,
        "render": project.render, **project.reserved, "thumbnail_png_b64": project.thumbnail_png_b64,
    }  # fmt: skip
    if project.timeline is not None:
        data["timeline"] = timeline_dict(project.timeline)
    if project.bookmarks:
        data["camera_bookmarks"] = {name: camera_to_dict(camera) for name, camera in project.bookmarks.items()}
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
        camera=camera_from_dict(data.get("camera")),
        camera_lock_to_script=bool(data.get("camera_lock_to_script", False)),
        render=dict(data.get("render") or {}), thumbnail_png_b64=str(data.get("thumbnail_png_b64", "")),
        timeline=timeline_from(data["timeline"]) if data.get("timeline") else None,
        reserved={k: data[k] for k in RESERVED if k in data}, bookmarks=_bookmarks(data.get("camera_bookmarks")),
    )  # fmt: skip


def _bookmarks(data: Any) -> dict[str, Camera]:
    if not isinstance(data, dict):
        return {}
    cameras = {str(name): camera_from_dict(value) for name, value in data.items()}
    return {name: camera for name, camera in cameras.items() if camera is not None}


def load(path: Path) -> Project:
    return from_json(path.read_text(encoding="utf-8"), path.parent)


def save(path: Path, project: Project, dialect: int = 1) -> None:
    """Write the project file. A linked script is not written here: its editor tab saves the .es file."""
    path.write_text(to_json(project, dialect), encoding="utf-8")
