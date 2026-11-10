"""Camera tracks (docs/16 §2.1): 'camera:eye.x' … 'camera:target.z', 'camera:fov', and the lens's
'camera:focus' (a focus pull; keyed as the distance in focus) and 'camera:fstop' (0: no depth of field)."""

from __future__ import annotations

from dataclasses import replace

from ..scene.camera import Camera
from .timeline import CAMERA_FIELDS, Timeline


def camera_values(camera: Camera) -> dict[str, float]:
    """Returns the keyable fields of a camera by track target ('camera:eye.x' … 'camera:fstop').

    Args:
        camera: The camera; a lens without an f-stop gives 0 for 'camera:fstop'.
    """
    values = [*camera.eye, *camera.target, camera.fov_y_deg, camera.focus, camera.lens.fstop or 0.0]
    return {f"camera:{name}": float(v) for name, v in zip(CAMERA_FIELDS, values, strict=True)}


def has_camera_tracks(timeline: Timeline) -> bool:
    return any(t.target.startswith("camera:") for t in timeline.tracks)


def camera_at(timeline: Timeline, frame: float, base: Camera) -> Camera:
    """Evaluates the camera tracks of a timeline.

    Args:
        timeline: The timeline with the camera tracks.
        frame: The frame (fractions interpolate).
        base: The camera whose un-animated fields are kept.

    Returns:
        ``base`` with every animated field at its value for ``frame``; a focus track focuses manually, an
        f-stop track of 0 or less removes the f-stop.
    """
    current = camera_values(base)
    values = {k: (timeline.value(k, frame) if timeline.track(k) else v) for k, v in current.items()}
    v = [values[f"camera:{name}"] for name in CAMERA_FIELDS]
    camera = replace(base, eye=(v[0], v[1], v[2]), target=(v[3], v[4], v[5]), fov_y_deg=v[6])  # type: ignore[arg-type]
    focus, fstop = float(v[7] or 0.0), float(v[8] or 0.0)
    if timeline.track("camera:focus"):
        camera = camera.focused_at(focus)
    if timeline.track("camera:fstop"):
        camera = camera.with_lens(fstop=fstop if fstop > 0 else None)
    return camera


def key_camera(timeline: Timeline, frame: int, camera: Camera) -> Timeline:
    """Keys every camera field at ``frame``."""
    for target, value in camera_values(camera).items():
        timeline = timeline.set_key(target, frame, value)
    return timeline
