"""The post stack (PLAN F1): what turns the linear render into a finished picture besides exposure and the view
transform — bloom (light spilling around bright highlights and emitters), vignette, white balance, saturation,
contrast and a grading LUT. Applied when an image is shown or saved (render/output.to_display), never to the
linear radiance itself (EXR files keep it untouched), so every change is live and free.

Order: bloom, vignette, temperature and saturation on linear light; then the view transform; then contrast and
the LUT on display values. Bloom adds intensity × the light above the threshold, spread by a Gaussian pyramid:
the energy it adds is exactly that, so a bloom never brightens what does not glow."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np

from .lut import apply_lut, load_cube

LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)
LEVELS = 6  # pyramid levels of the bloom (each halves the size)


@dataclass(frozen=True)
class PostSettings:
    bloom: float = 0.0  # intensity: 0 = off, 0.05 subtle, 0.3 neon
    bloom_threshold: float = 1.0  # linear luminance above which light blooms
    bloom_radius: float = 0.5  # 0 tight … 1 wide (the weight of the coarse pyramid levels)
    vignette: float = 0.0  # 0 … 1: how dark the corners get
    temperature: float = 0.0  # −1 cool (blue) … 1 warm (amber)
    saturation: float = 1.0  # 0 grey … 2 vivid
    contrast: float = 1.0  # around mid grey, on display values
    lut: str = ""  # a .cube file (relative to the script's folder)

    @property
    def active(self) -> bool:
        return self != PostSettings()


RANGES: dict[str, tuple[float, float]] = {  # render-block values are clamped to these (catalog/v2_blocks.toml)
    "bloom": (0.0, 2.0),
    "bloom_threshold": (0.0, 100.0),
    "bloom_radius": (0.0, 1.0),
    "vignette": (0.0, 1.0),
    "temperature": (-1.0, 1.0),
    "saturation": (0.0, 2.0),
    "contrast": (0.0, 2.0),
}

LOOKS: dict[str, PostSettings] = {
    "Off": PostSettings(),
    "Subtle": PostSettings(bloom=0.04, vignette=0.15, saturation=1.05, contrast=1.05),
    "Neon": PostSettings(bloom=0.3, bloom_threshold=0.8, bloom_radius=0.7, saturation=1.2, contrast=1.1),
    "Cinematic": PostSettings(bloom=0.08, vignette=0.35, temperature=0.15, saturation=0.9, contrast=1.15),
    "Studio": PostSettings(vignette=0.1, contrast=1.08),
}


def look_named(name: str) -> PostSettings | None:
    """A look by name, any case ('neon' in a script, 'Neon' in the tool bar)."""
    return next((post for key, post in LOOKS.items() if key.lower() == name.lower()), None)


def adjusted(base: PostSettings, values: Mapping[str, object]) -> PostSettings:
    """``base`` with ``values`` over it: numbers for RANGES keys (clamped), a file name for 'lut'."""
    changes: dict[str, Any] = {}
    for key, (low, high) in RANGES.items():
        value = values.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            changes[key] = min(high, max(low, float(value)))
    if values.get("lut"):
        changes["lut"] = str(values["lut"])
    return replace(base, **changes)


def post_from_block(block: Mapping[str, object]) -> PostSettings | None:
    """The post stack a v2 render block declares: its 'look' (default none), then the single keys over it; None
    when the block declares none of it."""
    base = look_named(str(block.get("look", "")))
    if base is None and not any(key in block for key in (*RANGES, "lut")):
        return None
    return adjusted(base or PostSettings(), block)


def _down(image: np.ndarray) -> np.ndarray:
    h, w = (image.shape[0] // 2) * 2, (image.shape[1] // 2) * 2
    if h < 2 or w < 2:
        return image
    q = image[:h, :w]
    out: np.ndarray = ((q[0::2, 0::2] + q[1::2, 0::2] + q[0::2, 1::2] + q[1::2, 1::2]) * 0.25).astype(np.float32)
    return out


def _blur(image: np.ndarray, taps: tuple[float, ...] = (1, 4, 6, 4, 1)) -> np.ndarray:
    """A binomial blur (default 5 taps, 1 4 6 4 1) along both image axes, edges clamped."""
    weights = np.asarray(taps, np.float32) / np.float32(sum(taps))
    half = len(taps) // 2
    out = image
    for axis in (0, 1):
        padded = np.pad(out, [(half, half) if a == axis else (0, 0) for a in range(out.ndim)], mode="edge")
        n, index = out.shape[axis], [slice(None)] * out.ndim
        total = np.zeros_like(out)
        for k, weight in enumerate(weights):
            index[axis] = slice(k, k + n)
            total += padded[tuple(index)] * weight
        out = total
    return out


def _up(image: np.ndarray, shape: tuple[int, ...]) -> np.ndarray:
    """Twice the size (cropped or edge-extended to ``shape``), smoothed by a 3-tap tent."""
    rows = np.minimum(np.arange(shape[0]) // 2, image.shape[0] - 1)
    cols = np.minimum(np.arange(shape[1]) // 2, image.shape[1] - 1)
    return _blur(image[rows][:, cols], (1, 2, 1))


def bloom_light(image: np.ndarray, threshold: float, radius: float) -> np.ndarray:
    """The light above ``threshold`` spread over the image by a Gaussian-like pyramid (from half resolution:
    fast enough to apply live); its sum equals the light it took."""
    luma = image @ LUMA
    bright = image * (np.maximum(luma - threshold, 0.0) / np.maximum(luma, 1e-6))[..., None]
    total = float(bright.sum())
    if total <= 0.0:
        return np.zeros_like(image)
    levels = [_blur(_down(bright))]
    for _ in range(LEVELS - 1):
        levels.append(_blur(_down(levels[-1])))
    weights = [(1.0 - radius) ** 2 + 0.05, *(0.5 + radius * k for k in range(1, LEVELS))]
    spread: np.ndarray = levels[-1] * np.float32(weights[-1])
    for level, weight in zip(reversed(levels[:-1]), reversed(weights[:-1]), strict=True):
        spread = _up(spread, level.shape) + level * np.float32(weight)
    spread = _up(spread, image.shape)
    return spread * np.float32(total / max(float(spread.sum()), 1e-12))


def vignette_factor(height: int, width: int, amount: float) -> np.ndarray:
    y, x = np.mgrid[0:height, 0:width].astype(np.float32)
    r = np.hypot((x + 0.5) / width - 0.5, (y + 0.5) / height - 0.5) / np.float32(np.hypot(0.5, 0.5))
    t = np.clip((r - 0.3) / 0.7, 0.0, 1.0)
    out: np.ndarray = (1.0 - amount * t * t * (3 - 2 * t))[..., None].astype(np.float32)
    return out


def apply_linear(image: np.ndarray, post: PostSettings) -> np.ndarray:
    """Bloom, vignette, white balance and saturation on linear light."""
    out: np.ndarray = image.astype(np.float32)
    if post.bloom > 0:
        out = out + bloom_light(out, post.bloom_threshold, post.bloom_radius) * np.float32(post.bloom)
    if post.vignette > 0:
        out = out * vignette_factor(out.shape[0], out.shape[1], post.vignette)
    if post.temperature:
        t = np.float32(0.2 * post.temperature)
        out = out * np.array([1 + t, 1.0, 1 - t], np.float32)
    if post.saturation != 1.0:
        luma = (out @ LUMA)[..., None]
        out = np.maximum(luma + (out - luma) * np.float32(post.saturation), 0.0)
    return out


def apply_display(rgb: np.ndarray, post: PostSettings, asset_dir: str = "") -> np.ndarray:
    """Contrast and the LUT on display values (float 0..1 after the view transform)."""
    out = rgb
    if post.contrast != 1.0:
        out = np.clip(0.5 + (out - 0.5) * np.float32(post.contrast), 0.0, 1.0)
    if post.lut:
        path = Path(post.lut).expanduser()
        path = path if path.is_absolute() or not asset_dir else Path(asset_dir) / path
        out = apply_lut(out, load_cube(path))
    return out.astype(np.float32)
