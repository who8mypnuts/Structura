"""Physical camera and the exact conversion from Structure Synth's view transform (docs/07 §5).

Legacy view: V = T(translation) · S(scale) · R · T(−pivot), perspective fovy = 'perspective-angle'.
A uniform world scale in front of a perspective camera equals moving the eye by 1/s, so
    eye = pivot + Rᵀ(−t/s),  forward = Rᵀ(0,0,−1),  up = Rᵀ(0,1,0),  target = eye + forward·|t_z|/s.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np

Vec3 = tuple[float, float, float]
LEGACY_TRANSLATION: Vec3 = (0.0, 0.0, -20.0)
LEGACY_SCALE = 0.4
LEGACY_FOV = 22.0


@dataclass(frozen=True)
class Camera:
    eye: Vec3
    target: Vec3
    up: Vec3 = (0.0, 1.0, 0.0)
    fov_y_deg: float = LEGACY_FOV
    aperture_radius: float = 0.0
    focus_distance: float | None = None

    @property
    def basis(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """(forward, right, up) orthonormal, right-handed, looking along forward."""
        forward = np.subtract(self.target, self.eye).astype(np.float64)
        forward /= np.linalg.norm(forward)
        right = np.cross(forward, self.up)
        right /= np.linalg.norm(right)
        return forward, right, np.cross(right, forward)

    @property
    def focus(self) -> float:
        return self.focus_distance or float(np.linalg.norm(np.subtract(self.target, self.eye)))


@dataclass(frozen=True)
class LegacyView:
    translation: Vec3 = LEGACY_TRANSLATION
    rotation: tuple[float, ...] = field(default=(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0))  # row-major
    pivot: Vec3 = (0.0, 0.0, 0.0)
    scale: float = LEGACY_SCALE
    fov_y_deg: float = LEGACY_FOV

    def camera(self) -> Camera:
        r = np.asarray(self.rotation, np.float64).reshape(3, 3)
        t, s = np.asarray(self.translation, np.float64), self.scale
        eye = np.asarray(self.pivot) + r.T @ (-t / s)
        forward = r.T @ np.array([0.0, 0.0, -1.0])
        up = r.T @ np.array([0.0, 1.0, 0.0])
        target = eye + forward * (abs(t[2]) / s)
        return Camera(_vec(eye), _vec(target), _vec(up), self.fov_y_deg)


def _vec(v: np.ndarray) -> Vec3:
    return (float(v[0]), float(v[1]), float(v[2]))


def framed(camera: Camera, lo: np.ndarray, hi: np.ndarray, aspect: float, margin: float = 1.1) -> Camera:
    """Move the eye along the view direction so the bounding box [lo, hi] fits the frame."""
    centre = (np.asarray(lo) + np.asarray(hi)) / 2
    radius = float(np.linalg.norm(np.asarray(hi) - np.asarray(lo))) / 2 or 1.0
    half = math.radians(camera.fov_y_deg) / 2
    fit = min(half, math.atan(math.tan(half) * aspect))
    distance = radius * margin / math.sin(fit)
    forward, _, up = camera.basis
    eye = centre - forward * distance
    return replace(camera, eye=_vec(eye), target=_vec(centre), up=_vec(up))


STANDARD_VIEWS: dict[str, tuple[Vec3, Vec3]] = {  # name → (direction from the centre to the eye, up)
    "front": ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),
    "back": ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
    "right": ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
    "left": ((-1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
    "top": ((0.0, 1.0, 0.0), (0.0, 0.0, -1.0)),
    "bottom": ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
    "iso": ((0.577350269, 0.577350269, 0.577350269), (0.0, 1.0, 0.0)),
}


def standard_view(name: str, lo: np.ndarray, hi: np.ndarray, aspect: float, fov_y_deg: float = LEGACY_FOV) -> Camera:
    """Look at the bounding box [lo, hi] along a principal axis (or the isometric diagonal), framed."""
    direction, up = STANDARD_VIEWS[name]
    centre = (np.asarray(lo, np.float64) + np.asarray(hi, np.float64)) / 2
    start = Camera(_vec(centre + np.asarray(direction)), _vec(centre), up, fov_y_deg)
    return framed(start, lo, hi, aspect)
