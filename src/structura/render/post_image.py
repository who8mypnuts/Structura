"""The post stack's image operations (render/post.py has the settings): bloom, vignette, white balance and
saturation on linear light, then contrast and the LUT on display values. render/output.Display applies them
where images are shown and saved, never to the radiance itself."""

from __future__ import annotations

import logging
from functools import cache
from pathlib import Path

import numpy as np

from .lut import apply_lut, load_cube
from .post import PostSettings
from .views import LUMA

log = logging.getLogger(__name__)
LEVELS = 6  # pyramid levels of the bloom (each halves the size)


def _down(image: np.ndarray) -> np.ndarray:
    """Half the size (odd last rows and columns dropped) by averaging 2 × 2 blocks; tiny images stay."""
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
    """Spreads the light above a threshold over the image.

    A Gaussian-like pyramid starting at half resolution (fast enough to apply live); the result is normalised so
    its sum equals the light taken, so bloom adds exactly ``intensity ×`` that light and never brightens an image
    with nothing above the threshold.

    Args:
        image: float32 linear RGB (H, W, 3).
        threshold: Linear luminance above which light blooms.
        radius: 0 a tight halo … 1 a wide glow.

    Returns:
        The spread light, float32 (H, W, 3).
    """
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
    """Returns the vignette's per-pixel factor, float32 (height, width, 1).

    Args:
        height: Image height in pixels.
        width: Image width in pixels.
        amount: 0 (no change) … 1 (black corners); the centre third of the image is never darkened.
    """
    y, x = np.mgrid[0:height, 0:width].astype(np.float32)
    r = np.hypot((x + 0.5) / width - 0.5, (y + 0.5) / height - 0.5) / np.float32(np.hypot(0.5, 0.5))
    t = np.clip((r - 0.3) / 0.7, 0.0, 1.0)
    out: np.ndarray = (1.0 - amount * t * t * (3 - 2 * t))[..., None].astype(np.float32)
    return out


def apply_linear(image: np.ndarray, post: PostSettings) -> np.ndarray:
    """Applies bloom, vignette, white balance and saturation to linear light.

    Args:
        image: Linear RGB (H, W, 3).
        post: The post stack.

    Returns:
        A new float32 image.
    """
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
    """Applies contrast and the LUT to display values.

    Args:
        rgb: float display values in 0..1 (after the view transform), any shape ending in 3.
        post: The post stack.
        asset_dir: The folder a relative LUT path is relative to (the script's).

    Returns:
        float32 display values. A LUT that cannot be read is skipped with a logged warning: a look never stops
        an image from being shown or saved.
    """
    out = rgb
    if post.contrast != 1.0:
        out = np.clip(0.5 + (out - 0.5) * np.float32(post.contrast), 0.0, 1.0)
    if post.lut:
        path = Path(post.lut).expanduser()
        path = path if path.is_absolute() or not asset_dir else Path(asset_dir) / path
        try:
            out = apply_lut(out, load_cube(path))
        except (OSError, ValueError) as exc:
            _warn_once(str(path), str(exc))
    return out.astype(np.float32)


@cache
def _warn_once(path: str, problem: str) -> None:
    """Logs an unusable LUT once per path and problem (images are redisplayed often)."""
    log.warning("LUT %s skipped: %s", path, problem)
