"""Environment maps for the path tracer (docs/10 §4): an HDRI file, or the Preetham sun-sky baked into an
equirectangular map, plus the tables for importance sampling (2-D marginal/conditional CDF weighted by
luminance × sin θ). One kernel code path serves both ('env_f', 'env_cdf' buffers).

Map convention: rows go from the zenith (v = 0) to the nadir; u = 0.5 looks along −z (the default view),
and the direction is (sin θ sin φ, cos θ, −sin θ cos φ) with φ = 2π(u − 0.5) + rotation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from .hdr_io import read_environment
from .settings import SKY_GROUND, RenderSettings

RGB = tuple[float, float, float]
SKY_SIZE = (512, 256)
GROUND: RGB = SKY_GROUND
SKY_UNITS = 1.0 / 31.8  # kcd/m² → radiance units where the default sun lights white paper to ≈ 1
XYZ_TO_RGB = np.array([[3.2406, -1.5372, -0.4986], [-0.9689, 1.8758, 0.0415], [0.0557, -0.2040, 1.0570]])
PEREZ = {  # (slope, offset) per coefficient A..E and channel, Preetham et al. 1999
    "Y": ((0.1787, -1.4630), (-0.3554, 0.4275), (-0.0227, 5.3251), (0.1206, -2.5771), (-0.0670, 0.3703)),
    "x": ((-0.0193, -0.2592), (-0.0665, 0.0008), (-0.0004, 0.2125), (-0.0641, -0.8989), (-0.0033, 0.0452)),
    "y": ((-0.0167, -0.2608), (-0.0950, 0.0092), (-0.0079, 0.2102), (-0.0441, -1.6537), (-0.0109, 0.0529)),
}


@dataclass(frozen=True)
class EnvMap:
    rgb: np.ndarray  # float32 (height, width, 3), linear radiance
    cdf: np.ndarray  # float32: marginal (height + 1), then one conditional (width + 1) per row

    @property
    def width(self) -> int:
        return int(self.rgb.shape[1])

    @property
    def height(self) -> int:
        return int(self.rgb.shape[0])


def directions(width: int, height: int) -> np.ndarray:
    """Unit direction of every texel centre, (height, width, 3)."""
    theta = (np.arange(height) + 0.5) / height * math.pi
    phi = ((np.arange(width) + 0.5) / width - 0.5) * 2 * math.pi
    t, p = np.meshgrid(theta, phi, indexing="ij")
    return np.stack([np.sin(t) * np.sin(p), np.cos(t), -np.sin(t) * np.cos(p)], axis=-1)


def sampling_tables(rgb: np.ndarray) -> np.ndarray:
    """Marginal and conditional CDFs (importance ∝ luminance × sin θ, so pixels near the poles are smaller)."""
    height = rgb.shape[0]
    sin_theta = np.sin((np.arange(height) + 0.5) / height * math.pi)[:, None]
    weight = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]) * sin_theta + 1e-12
    rows = np.cumsum(weight, axis=1)
    conditional = np.hstack([np.zeros((height, 1)), rows / rows[:, -1:]])
    marginal = np.concatenate([[0.0], np.cumsum(rows[:, -1]) / rows[:, -1].sum()])
    return np.concatenate([marginal, conditional.ravel()]).astype(np.float32)


def _perez(theta: np.ndarray, gamma: np.ndarray, c: tuple[float, ...]) -> np.ndarray:
    a, b, cc, d, e = c
    cos_t = np.maximum(np.cos(theta), 0.01)
    return (1 + a * np.exp(b / cos_t)) * (1 + cc * np.exp(d * gamma) + e * np.cos(gamma) ** 2)


def _zenith(turbidity: float, theta_sun: float) -> tuple[float, float, float]:
    t, s = turbidity, theta_sun
    chi = (4 / 9 - t / 120) * (math.pi - 2 * s)
    luminance = (4.0453 * t - 4.9710) * math.tan(chi) - 0.2155 * t + 2.4192
    x = (t * t * (0.00166 * s**3 - 0.00375 * s**2 + 0.00209 * s)
         + t * (-0.02903 * s**3 + 0.06377 * s**2 - 0.03202 * s + 0.00394)
         + (0.11693 * s**3 - 0.21196 * s**2 + 0.06052 * s + 0.25886))  # fmt: skip
    y = (t * t * (0.00275 * s**3 - 0.00610 * s**2 + 0.00317 * s)
         + t * (-0.04214 * s**3 + 0.08970 * s**2 - 0.04153 * s + 0.00516)
         + (0.15346 * s**3 - 0.26756 * s**2 + 0.06670 * s + 0.26688))  # fmt: skip
    return max(luminance, 0.0), x, y


def preetham_sky(
    sun: RGB, turbidity: float = 3.0, ground: RGB = GROUND, size: tuple[int, int] = SKY_SIZE
) -> np.ndarray:
    """The Preetham clear sky for a sun direction (towards the sun), linear RGB (height, width, 3)."""
    width, height = size
    d = directions(width, height)
    s = np.asarray(sun, np.float64) / (np.linalg.norm(sun) or 1.0)
    theta_sun = math.acos(min(1.0, max(-1.0, s[1])))
    theta = np.arccos(np.clip(d[..., 1], -1.0, 1.0))
    gamma = np.arccos(np.clip(d @ s, -1.0, 1.0))
    zenith = _zenith(turbidity, min(theta_sun, math.pi / 2 - 0.01))
    channels = []
    for key, value in zip("Yxy", zenith, strict=True):
        coefficients = tuple(slope * turbidity + offset for slope, offset in PEREZ[key])
        channels.append(value * _perez(theta, gamma, coefficients) / _perez(np.zeros(1), np.array([theta_sun]),
                                                                               coefficients))  # fmt: skip
    luminance, x, y = channels
    y = np.maximum(y, 1e-6)
    xyz = np.stack([x / y * luminance, luminance, (1 - x - y) / y * luminance], axis=-1)
    rgb = np.clip(xyz @ XYZ_TO_RGB.T, 0.0, None) * SKY_UNITS
    below = d[..., 1] < 0.0
    rgb[below] = np.asarray(ground) * float(np.pi * SKY_UNITS * zenith[0] * 0.5)  # a dim diffuse ground
    out: np.ndarray = rgb.astype(np.float32)
    return out


@lru_cache(maxsize=8)
def _file_map(path: str, mtime: float) -> EnvMap:
    rgb = read_environment(Path(path))
    return EnvMap(rgb, sampling_tables(rgb))


@lru_cache(maxsize=8)
def _sky_map(sun: RGB, turbidity: float, ground: RGB) -> EnvMap:
    rgb = preetham_sky(sun, turbidity, ground)
    return EnvMap(rgb, sampling_tables(rgb))


def environment_map(
    kind: str, file: str = "", sun: RGB = (0.0, 1.0, 0.0), turbidity: float = 3.0, ground: RGB = GROUND
) -> EnvMap | None:
    """The map for an environment type ('hdri', 'sunsky'); None for the analytic colour/gradient sky."""
    if kind == "hdri" and file:
        path = Path(file).expanduser()
        return _file_map(str(path.resolve()), path.stat().st_mtime)
    if kind == "sunsky":
        return _sky_map((float(sun[0]), float(sun[1]), float(sun[2])), float(turbidity),
                        (float(ground[0]), float(ground[1]), float(ground[2])))  # fmt: skip
    return None


def settings_environment(settings: RenderSettings) -> EnvMap | None:
    """The environment map a render uses (cached), from its settings."""
    file = settings.env_file
    if file and not Path(file).expanduser().is_absolute() and settings.asset_dir:
        file = str(Path(settings.asset_dir) / file)
    return environment_map(settings.env_type, file, settings.sun_direction, settings.turbidity, settings.ground)
