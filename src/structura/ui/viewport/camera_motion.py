"""Animated camera moves (docs/08 §7, docs/14 §1 "motion with purpose"): standard views, framing and saved
views glide over 200 ms instead of jumping, unless the user asked for reduced motion."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

import numpy as np
from PySide6.QtCore import QEasingCurve, QObject, QVariantAnimation

from ...core.scene.camera import Camera

DURATION_MS = 200


def _unit(v: np.ndarray, fallback: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-9 else fallback


def interpolate(a: Camera, b: Camera, t: float) -> Camera:
    """The camera a fraction ``t`` of the way from ``a`` to ``b``: target and distance move linearly, the view
    direction and up vector turn (normalised linear interpolation)."""
    fa, _, ua = a.basis
    fb, _, ub = b.basis
    target = np.add(np.multiply(a.target, 1 - t), np.multiply(b.target, t))
    da = float(np.linalg.norm(np.subtract(a.target, a.eye)))
    db = float(np.linalg.norm(np.subtract(b.target, b.eye)))
    forward = _unit(fa * (1 - t) + fb * t, fb)
    up = _unit(ua * (1 - t) + ub * t, ub)
    up = _unit(up - forward * float(np.dot(up, forward)), ub)
    eye = target - forward * (da * (1 - t) + db * t)
    fov = a.fov_y_deg * (1 - t) + b.fov_y_deg * t
    return replace(b, eye=_tuple(eye), target=_tuple(target), up=_tuple(up), fov_y_deg=fov)


def _tuple(v: np.ndarray) -> tuple[float, float, float]:
    return (float(v[0]), float(v[1]), float(v[2]))


class CameraMotion(QObject):
    def __init__(self, apply: Callable[[Camera], None], animate: Callable[[], bool], parent: QObject) -> None:
        super().__init__(parent)
        self.apply, self.animate = apply, animate
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(DURATION_MS)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self._step)
        self.start: Camera | None = None
        self.end: Camera | None = None

    def move(self, start: Camera, end: Camera) -> None:
        self.animation.stop()
        if not self.animate():
            self.apply(end)
            return
        self.start, self.end = start, end
        self.animation.start()

    def _step(self, t: object) -> None:
        if self.start is not None and self.end is not None:
            self.apply(self.end if float(t) >= 1.0 else interpolate(self.start, self.end, float(t)))  # type: ignore[arg-type]
