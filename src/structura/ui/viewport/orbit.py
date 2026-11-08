"""Viewport camera navigation (docs/08 §7): turntable orbit about the world Y axis that keeps any roll of
the starting camera (legacy views often have one), plus pan, dolly toward the target, and framing."""

from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from ...core.scene.camera import Camera, framed

WORLD_UP = np.array([0.0, 1.0, 0.0])


def rotate(v: np.ndarray, axis: np.ndarray, angle: float) -> np.ndarray:
    """Rodrigues rotation of v about the unit axis."""
    k = axis / (np.linalg.norm(axis) or 1.0)
    c, s = math.cos(angle), math.sin(angle)
    out: np.ndarray = v * c + np.cross(k, v) * s + k * np.dot(k, v) * (1 - c)
    return out


def _vec(v: np.ndarray) -> tuple[float, float, float]:
    return (float(v[0]), float(v[1]), float(v[2]))


class OrbitController:
    ORBIT_SPEED = 0.008  # radians per pixel
    PAN_SPEED = 0.0015  # distance fraction per pixel
    DOLLY_STEP = 0.88

    def __init__(self, camera: Camera | None = None) -> None:
        self.trackball = False  # True: orbit about the camera's own axes (Structure Synth 1.5), no pole stop
        self.set_camera(camera or Camera((0.0, 0.0, 10.0), (0.0, 0.0, 0.0)))

    def set_camera(self, camera: Camera) -> None:
        self.fov = camera.fov_y_deg
        self.base = camera
        self.target = np.asarray(camera.target, np.float64)
        offset = self.target - np.asarray(camera.eye, np.float64)
        self.distance = float(np.linalg.norm(offset)) or 1.0
        forward, _, up = camera.basis
        self.forward, self.up = forward.astype(np.float64), up.astype(np.float64)

    @property
    def right(self) -> np.ndarray:
        r = np.cross(self.forward, self.up)
        return r / (np.linalg.norm(r) or 1.0)

    def camera(self) -> Camera:
        eye = self.target - self.forward * self.distance
        return replace(self.base, eye=_vec(eye), target=_vec(self.target), up=_vec(self.up), fov_y_deg=self.fov)

    def orbit(self, dx: float, dy: float) -> None:
        yaw, pitch = -dx * self.ORBIT_SPEED, -dy * self.ORBIT_SPEED
        axis = self.up.copy() if self.trackball else WORLD_UP
        self.forward, self.up = rotate(self.forward, axis, yaw), rotate(self.up, axis, yaw)
        right = self.right
        new_forward, new_up = rotate(self.forward, right, pitch), rotate(self.up, right, pitch)
        if self.trackball or abs(float(np.dot(new_forward, WORLD_UP))) < 0.995:  # turntable: stop at the poles
            self.forward, self.up = new_forward, new_up
        self._orthonormalise()

    def roll(self, angle: float) -> None:
        self.up = rotate(self.up, self.forward, angle)
        self._orthonormalise()

    def pan(self, dx: float, dy: float) -> None:
        scale = self.distance * self.PAN_SPEED
        self.target = self.target - self.right * dx * scale + self.up * dy * scale

    def dolly(self, steps: float) -> None:
        self.distance = max(1e-4, self.distance * self.DOLLY_STEP**steps)

    def frame(self, lo: np.ndarray, hi: np.ndarray, aspect: float) -> None:
        self.set_camera(framed(self.camera(), lo, hi, aspect))

    def _orthonormalise(self) -> None:
        self.forward /= np.linalg.norm(self.forward)
        self.up = self.up - self.forward * np.dot(self.up, self.forward)
        self.up /= np.linalg.norm(self.up) or 1.0

    # -- first-person (fly) ------------------------------------------------------------------------------------
    @property
    def eye(self) -> np.ndarray:
        eye: np.ndarray = self.target - self.forward * self.distance
        return eye

    def look(self, dx: float, dy: float) -> None:
        """Turn the camera about its eye (the target moves), as when flying."""
        eye = self.eye
        self.orbit(dx, dy)
        self.target = eye + self.forward * self.distance

    def fly(self, right: float, up: float, forward: float) -> None:
        """Move eye and target together, in steps of a twentieth of the viewing distance."""
        step = self.distance * 0.05
        self.target = self.target + (self.right * right + self.up * up + self.forward * forward) * step
