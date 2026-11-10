"""Physical camera and the exact conversion from Structure Synth's view transform (docs/07 §5).

Legacy view: V = T(translation) · S(scale) · R · T(−pivot), perspective fovy = 'perspective-angle'.
A uniform world scale in front of a perspective camera equals moving the eye by 1/s, so
    eye = pivot + Rᵀ(−t/s),  forward = Rᵀ(0,0,−1),  up = Rᵀ(0,1,0),  target = eye + forward·|t_z|/s.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np

from .lens import Lens, focal_length_mm, fov_for, hyperfocal, pupil_radius, sharp_range
from .vectors import Vec3
from .vectors import as_vec3 as _vec

LEGACY_TRANSLATION: Vec3 = (0.0, 0.0, -20.0)
LEGACY_SCALE = 0.4
LEGACY_FOV = 22.0


@dataclass(frozen=True)
class Camera:
    """Where the camera is and what it sees.

    ``fov_y_deg`` is the one stored measure of the field of view: the focal length is derived from it and the
    lens's sensor. The lens (core/scene/lens.py) holds everything else.

    Attributes:
        eye: Position of the camera.
        target: The point looked at (also the default focus).
        up: The approximate up direction.
        fov_y_deg: Vertical field of view in degrees.
        lens: Projection, aperture, focus, bokeh, shift and tilt.
    """

    eye: Vec3
    target: Vec3
    up: Vec3 = (0.0, 1.0, 0.0)
    fov_y_deg: float = LEGACY_FOV
    lens: Lens = field(default_factory=Lens)

    @property
    def basis(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """(forward, right, up): orthonormal and right-handed, looking along forward.

        An ``up`` parallel to the view direction is replaced by another axis, so the basis is always defined.
        """
        forward = np.subtract(self.target, self.eye).astype(np.float64)
        forward /= np.linalg.norm(forward) or 1.0
        right = np.cross(forward, self.up)
        if np.linalg.norm(right) < 1e-12:  # looking straight along 'up'
            right = np.cross(forward, (1.0, 0.0, 0.0) if abs(forward[0]) < 0.9 else (0.0, 0.0, 1.0))
        right /= np.linalg.norm(right)
        return forward, right, np.cross(right, forward)

    @property
    def distance(self) -> float:
        """The distance from the eye to the target."""
        return float(np.linalg.norm(np.subtract(self.target, self.eye)))

    @property
    def focal_length_mm(self) -> float:
        """The focal length, in millimetres, that gives ``fov_y_deg`` on the lens's sensor."""
        return focal_length_mm(self.fov_y_deg, self.lens.sensor_mm[1])

    @property
    def aperture_radius(self) -> float:
        """The entrance-pupil radius in world units (0: a pinhole, everything sharp)."""
        return pupil_radius(self.lens, self.focal_length_mm) if self.lens.projection == "perspective" else 0.0

    @property
    def focus(self) -> float:
        """The distance in focus: the target's, a manual distance, or the hyperfocal distance."""
        lens = self.lens
        if lens.focus_mode == "manual" and lens.focus_distance:
            return lens.focus_distance
        if lens.focus_mode == "hyperfocal":
            h = hyperfocal(lens, self.focal_length_mm)
            if math.isfinite(h):
                return h
        return self.distance

    @property
    def focus_normal(self) -> np.ndarray:
        """The focus plane's unit normal: the view direction turned by the lens tilt (about x, then y)."""
        forward, right, up = self.basis
        tx, ty = (math.radians(a) for a in self.lens.tilt)
        n = forward * math.cos(tx) + up * math.sin(tx)
        n = n * math.cos(ty) + right * math.sin(ty)
        out: np.ndarray = n / (np.linalg.norm(n) or 1.0)
        return out

    @property
    def sharp_range(self) -> tuple[float, float]:
        """(near, far) distances of acceptable sharpness; (0, inf) without depth of field."""
        if self.aperture_radius <= 0.0:
            return 0.0, math.inf
        return sharp_range(self.lens, self.focal_length_mm, self.focus)

    @property
    def fstop(self) -> float:
        """The f-number: the lens's, or the one its aperture radius amounts to (inf for a pinhole)."""
        if self.lens.fstop:
            return self.lens.fstop
        radius = self.aperture_radius
        return self.lens.world(self.focal_length_mm) / (2.0 * radius) if radius > 0.0 else math.inf

    def with_lens(self, **changes: object) -> Camera:
        """Returns this camera with some lens fields changed.

        Args:
            **changes: Lens fields and their new values (``fstop=2.8``, ``blades=6`` …).

        Returns:
            The changed camera.
        """
        return replace(self, lens=replace(self.lens, **changes))  # type: ignore[arg-type]

    def focused_at(self, distance: float | None) -> Camera:
        """Returns this camera focused at a distance.

        Args:
            distance: The distance in focus, in world units; None focuses on the target again.

        Returns:
            The refocused camera.
        """
        if distance is None:
            return self.with_lens(focus_mode="target", focus_distance=None)
        return self.with_lens(focus_mode="manual", focus_distance=float(distance))

    def with_focal_length(self, mm: float) -> Camera:
        """Returns this camera with the field of view of a focal length on its sensor.

        Args:
            mm: The focal length in millimetres.

        Returns:
            The camera with the new ``fov_y_deg``.
        """
        return replace(self, fov_y_deg=fov_for(mm, self.lens.sensor_mm[1]))


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
