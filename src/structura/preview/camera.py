"""View and projection matrices for the preview engine (row-major numpy; upload transposed for GLSL).

Uses the same Camera as the precision engine, so both engines frame a scene identically (docs/08 §2).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ..core.scene.camera import Camera


def look_at(eye: np.ndarray, target: np.ndarray, up: np.ndarray) -> np.ndarray:
    f = target - eye
    f = f / np.linalg.norm(f)
    r = np.cross(f, up)
    r = r / (np.linalg.norm(r) or 1.0)
    u = np.cross(r, f)
    m = np.eye(4)
    m[0, :3], m[1, :3], m[2, :3] = r, u, -f
    m[:3, 3] = -m[:3, :3] @ eye
    return m


def perspective(fov_y_deg: float, aspect: float, near: float, far: float) -> np.ndarray:
    f = 1.0 / math.tan(math.radians(fov_y_deg) / 2.0)
    m = np.zeros((4, 4))
    m[0, 0], m[1, 1] = f / aspect, f
    m[2, 2], m[2, 3] = (far + near) / (near - far), 2.0 * far * near / (near - far)
    m[3, 2] = -1.0
    return m


def orthographic(half_height: float, aspect: float, near: float, far: float) -> np.ndarray:
    m = np.eye(4)
    m[0, 0], m[1, 1] = 1.0 / (half_height * aspect), 1.0 / half_height
    m[2, 2], m[2, 3] = -2.0 / (far - near), -(far + near) / (far - near)
    return m


@dataclass(frozen=True)
class Matrices:
    view: np.ndarray
    proj: np.ndarray
    ortho: bool = False

    @property
    def inv_proj(self) -> np.ndarray:
        return np.linalg.inv(self.proj)

    @property
    def inv_view(self) -> np.ndarray:
        return np.linalg.inv(self.view)


def camera_matrices(camera: Camera, aspect: float, lo: np.ndarray, hi: np.ndarray) -> Matrices:
    """Perspective matrices with near/far planes fitted to the scene bounds [lo, hi]."""
    eye = np.asarray(camera.eye, np.float64)
    view = look_at(eye, np.asarray(camera.target, np.float64), np.asarray(camera.up, np.float64))
    centre, radius = (lo + hi) / 2.0, max(float(np.linalg.norm(hi - lo)) / 2.0, 1e-3)
    distance = float(-(view @ np.append(centre, 1.0))[2])
    far = max(distance + radius * 1.5, 1e-2)
    near = max(distance - radius * 1.5, far * 1e-4)
    return Matrices(view, perspective(camera.fov_y_deg, aspect, near, far))


def gl(m: np.ndarray) -> bytes:
    """Column-major float32 bytes for a GLSL mat4 uniform."""
    return np.ascontiguousarray(m.T, np.float32).tobytes()
