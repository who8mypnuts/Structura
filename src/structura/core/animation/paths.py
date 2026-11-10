"""Camera paths written as timeline keys (PLAN F2): a turntable orbit, or a path through saved views.

Both produce ordinary camera tracks (core/animation/camera.py), so the timeline shows them, the user can edit
them, and `structura animate` renders a project's path like any other keys.

A turntable turns the eye about the camera's up axis through its target. It keys every frame (linear), so the
camera stays on the circle (keys interpolate straight lines); frame ``start + frames`` would equal the first
frame, so the range it sets — ``frames`` frames — loops seamlessly. With ``ease`` the turn starts and stops
gently and ends exactly at ``turns`` (a presentation move, not a loop); ``zoom`` moves the eye to that share of
its distance by the last frame (focus set to the target follows it: a focus pull for free)."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, replace

import numpy as np

from ..scene.camera import Camera
from .camera import key_camera
from .timeline import CAMERA_FIELDS, Interp, Timeline

EYE_AND_TARGET = tuple(f"camera:{name}" for name in CAMERA_FIELDS[:6])


@dataclass(frozen=True)
class Turntable:
    frames: int = 120  # frames per loop (5 s at 24 fps)
    turns: float = 1.0  # full turns over the frames
    clockwise: bool = False  # seen from above (along the up axis)
    elevation_deg: float | None = None  # raise or lower the eye to this angle above the target; None: keep it
    start: int = 0
    ease: bool = False  # smooth start and stop, ending at the full turns (not a seamless loop)
    zoom: float = 1.0  # the eye's distance at the end, as a share of the start (0.7: a third closer)


def _rotate(v: np.ndarray, axis: np.ndarray, angle: float) -> np.ndarray:
    """``v`` turned by ``angle`` radians about the unit ``axis`` (Rodrigues)."""
    c, s = math.cos(angle), math.sin(angle)
    return v * c + np.cross(axis, v) * s + axis * float(np.dot(axis, v)) * (1 - c)


def _elevated(offset: np.ndarray, up: np.ndarray, elevation_deg: float) -> np.ndarray:
    """``offset`` (target → eye) at ``elevation_deg`` above the plane normal to ``up``, same distance."""
    distance = float(np.linalg.norm(offset))
    flat = offset - up * float(np.dot(offset, up))
    flat = flat / (np.linalg.norm(flat) or 1.0)
    angle = math.radians(elevation_deg)
    return (flat * math.cos(angle) + up * math.sin(angle)) * distance


def turntable_eyes(camera: Camera, spec: Turntable) -> list[tuple[float, float, float]]:
    """The eye position of each of the ``spec.frames`` frames."""
    target = np.asarray(camera.target, np.float64)
    up = np.asarray(camera.up, np.float64)
    up = up / (np.linalg.norm(up) or 1.0)
    offset = np.asarray(camera.eye, np.float64) - target
    if spec.elevation_deg is not None:
        offset = _elevated(offset, up, spec.elevation_deg)
    sign = -1.0 if spec.clockwise else 1.0
    eyes = []
    for i in range(spec.frames):
        t = i / max(1, spec.frames - 1) if spec.ease else i / max(1, spec.frames)
        t = t * t * (3.0 - 2.0 * t) if spec.ease else t
        scale = 1.0 + (spec.zoom - 1.0) * t
        eye = target + _rotate(offset, up, sign * 2 * math.pi * spec.turns * t) * scale
        eyes.append((float(eye[0]), float(eye[1]), float(eye[2])))
    return eyes


def without_camera_path(timeline: Timeline) -> Timeline:
    """``timeline`` without eye and target tracks (a new path replaces the old one; lens tracks stay)."""
    return replace(timeline, tracks=tuple(t for t in timeline.tracks if t.target not in EYE_AND_TARGET))


def turntable(timeline: Timeline, camera: Camera, spec: Turntable) -> Timeline:
    """``timeline`` with a turntable of ``camera`` keyed from ``spec.start``, its range set to the loop."""
    out = without_camera_path(timeline)
    for i, eye in enumerate(turntable_eyes(camera, spec)):
        frame = spec.start + i
        for axis, value in zip("xyz", eye, strict=True):
            out = out.set_key(f"camera:eye.{axis}", frame, value, Interp.LINEAR)
        if i == 0:
            for axis, value in zip("xyz", camera.target, strict=True):
                out = out.set_key(f"camera:target.{axis}", frame, float(value), Interp.LINEAR)
    return replace(out, start=spec.start, end=spec.start + max(1, spec.frames) - 1)


def path_through(timeline: Timeline, cameras: Sequence[Camera], frames_each: int, start: int = 0) -> Timeline:
    """``timeline`` with a smooth camera path through ``cameras`` (saved views), ``frames_each`` frames apart,
    its range set to the path (a path needs two views or more; fewer leave ``timeline`` unchanged)."""
    if len(cameras) < 2:
        return timeline
    out = without_camera_path(timeline)
    for i, camera in enumerate(cameras):
        out = key_camera(out, start + i * frames_each, camera)
    return replace(out, start=start, end=start + (len(cameras) - 1) * frames_each)
