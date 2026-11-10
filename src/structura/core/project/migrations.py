"""Project-file migrations (docs/07 §8): each entry upgrades a raw JSON object from version N to N + 1.
A new format version adds one function here; loading runs the chain up to the current version."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

CURRENT_VERSION = 2
Migration = Callable[[dict[str, Any]], dict[str, Any]]
# Render Settings overrides of format 1 that describe the lens (format 2 keeps them in camera.lens)
LENS_KEYS = {"camera_type": "projection", "ortho_height": "ortho_height", "fisheye_fov": "fisheye_fov_deg",
             "blades": "blades", "blade_rotation_deg": "blade_rotation_deg", "aperture": "aperture_radius",
             "focus_distance": "focus_distance"}  # fmt: skip


def lens_into_camera(data: dict[str, Any]) -> dict[str, Any]:
    """1 → 2: the camera gained a lens; the lens settings the Render Settings panel held move into it."""
    render = dict(data.get("render") or {})
    lens = {new: render.pop(old) for old, new in LENS_KEYS.items() if old in render}
    camera = data.get("camera")
    if isinstance(camera, dict):
        moved = {k: camera.pop(k) for k in ("aperture_radius", "focus_distance") if k in camera}
        camera["lens"] = {**moved, **(camera.get("lens") or {}), **lens}
        if camera["lens"].get("focus_distance") is not None:
            camera["lens"].setdefault("focus_mode", "manual")
    return {**data, "render": render}


MIGRATIONS: dict[int, Migration] = {1: lens_into_camera}  # version -> function producing version + 1


class NewerProjectError(ValueError):
    """The file was written by a newer Structura."""


def migrate(data: dict[str, Any]) -> dict[str, Any]:
    version = int(data.get("format_version", 1))
    if version > CURRENT_VERSION:
        raise NewerProjectError(f"project format {version} is newer than this Structura ({CURRENT_VERSION})")
    while version < CURRENT_VERSION:
        data = MIGRATIONS[version](data)
        version += 1
        data["format_version"] = version
    return data
