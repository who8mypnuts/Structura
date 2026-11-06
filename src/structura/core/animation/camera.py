"""Camera tracks (docs/16 §2.1): 'camera:eye.x' … 'camera:target.z' and 'camera:fov'."""

from __future__ import annotations

from dataclasses import replace

from ..scene.camera import Camera
from .timeline import CAMERA_FIELDS, Timeline


def camera_values(camera: Camera) -> dict[str, float]:
    """The keyable fields of a camera, by track target."""
    values = [*camera.eye, *camera.target, camera.fov_y_deg]
    return {f"camera:{name}": float(v) for name, v in zip(CAMERA_FIELDS, values, strict=True)}


def has_camera_tracks(timeline: Timeline) -> bool:
    return any(t.target.startswith("camera:") for t in timeline.tracks)


def camera_at(timeline: Timeline, frame: float, base: Camera) -> Camera:
    """``base`` with every animated field replaced by its value at ``frame``."""
    current = camera_values(base)
    values = {k: (timeline.value(k, frame) if timeline.track(k) else v) for k, v in current.items()}
    v = [values[f"camera:{name}"] for name in CAMERA_FIELDS]
    return replace(base, eye=(v[0], v[1], v[2]), target=(v[3], v[4], v[5]), fov_y_deg=v[6])  # type: ignore[arg-type]


def key_camera(timeline: Timeline, frame: int, camera: Camera) -> Timeline:
    """Keys every camera field at ``frame``."""
    for target, value in camera_values(camera).items():
        timeline = timeline.set_key(target, frame, value)
    return timeline
