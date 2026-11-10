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
from ..scene.vectors import Vec3, as_vec3, rotate
from .camera import key_camera
from .timeline import CAMERA_FIELDS, Interp, Timeline

EYE_AND_TARGET = tuple(f"camera:{name}" for name in CAMERA_FIELDS[:6])


@dataclass(frozen=True)
class Turntable:
    """How a turntable moves the camera.

    Attributes:
        frames: Frames in the move (120 is 5 s at 24 fps).
        turns: Full turns over those frames.
        clockwise: The direction, seen from above (along the camera's up axis).
        elevation_deg: Raise or lower the eye to this angle above the target; None keeps its height.
        start: The first frame.
        ease: Start and stop gently and end exactly at ``turns`` (a presentation move, not a loop).
        zoom: The eye's distance at the end, as a share of the start (0.7: 30 % closer).
    """

    frames: int = 120
    turns: float = 1.0
    clockwise: bool = False
    elevation_deg: float | None = None
    start: int = 0
    ease: bool = False
    zoom: float = 1.0


def _elevated(offset: np.ndarray, up: np.ndarray, elevation_deg: float) -> np.ndarray:
    """``offset`` (target → eye) turned to ``elevation_deg`` above the plane normal to ``up``, same length."""
    distance = float(np.linalg.norm(offset))
    flat = offset - up * float(np.dot(offset, up))
    flat = flat / (np.linalg.norm(flat) or 1.0)
    angle = math.radians(elevation_deg)
    return (flat * math.cos(angle) + up * math.sin(angle)) * distance


def _progress(i: int, spec: Turntable) -> float:
    """How far through the move frame ``i`` is: i / frames for a loop (the last frame stops one step short
    of the first), a smoothstep from 0 to exactly 1 when eased."""
    if not spec.ease:
        return i / max(1, spec.frames)
    t = i / max(1, spec.frames - 1)
    return t * t * (3.0 - 2.0 * t)


def turntable_eyes(camera: Camera, spec: Turntable) -> list[Vec3]:
    """Computes the eye position of every frame of a turntable.

    Args:
        camera: The starting camera; the eye turns about its up axis through its target.
        spec: The move.

    Returns:
        ``spec.frames`` eye positions (none for zero frames).
    """
    target = np.asarray(camera.target, np.float64)
    up = np.asarray(camera.up, np.float64)
    up = up / (np.linalg.norm(up) or 1.0)
    offset = np.asarray(camera.eye, np.float64) - target
    if spec.elevation_deg is not None:
        offset = _elevated(offset, up, spec.elevation_deg)
    sign = -1.0 if spec.clockwise else 1.0
    eyes = []
    for i in range(max(0, spec.frames)):
        t = _progress(i, spec)
        turned = rotate(offset, up, sign * 2.0 * math.pi * spec.turns * t)
        eyes.append(as_vec3(target + turned * (1.0 + (spec.zoom - 1.0) * t)))
    return eyes


def without_camera_path(timeline: Timeline) -> Timeline:
    """Removes the eye and target tracks (a new path replaces the old one; lens tracks stay).

    Args:
        timeline: The timeline to clean (its range and other tracks stay).

    Returns:
        The timeline without those tracks.
    """
    return replace(timeline, tracks=tuple(t for t in timeline.tracks if t.target not in EYE_AND_TARGET))


def turntable(timeline: Timeline, camera: Camera, spec: Turntable) -> Timeline:
    """Keys a turntable into a timeline.

    Every frame is keyed (linear keys between frames would cut across the circle); the target is keyed once.

    Args:
        timeline: The timeline; its eye and target tracks are replaced, other tracks stay.
        camera: The starting camera.
        spec: The move.

    Returns:
        The new timeline, its range set to the move's frames.
    """
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
    """Keys a smooth camera path through saved views.

    Args:
        timeline: The timeline; its eye and target tracks are replaced, other tracks stay.
        cameras: The views, in order; every keyable field (lens included) moves between them.
        frames_each: Frames from one view to the next (at least 1).
        start: The frame of the first view.

    Returns:
        The new timeline, its range set to the path; ``timeline`` itself when there are fewer than two views.
    """
    if len(cameras) < 2:
        return timeline
    step = max(1, frames_each)
    out = without_camera_path(timeline)
    for i, camera in enumerate(cameras):
        out = key_camera(out, start + i * step, camera)
    return replace(out, start=start, end=start + (len(cameras) - 1) * step)
