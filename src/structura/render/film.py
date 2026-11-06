"""The film (docs/09 §5.3, §6): resolving the accumulation buffer and the adaptive sampler's noise test.

'accum' holds layout.FILM_F floats per pixel: the RGB and weight sums of all samples, then of the
even-numbered samples only. The two estimates differ by about the standard error, which gives a per-pixel
noise measure without storing squared sums (the approach of Cycles' adaptive sampling).
"""

from __future__ import annotations

import numpy as np

from .kernels.layout import FILM_F

EPSILON = 1e-4


def new_film(width: int, height: int) -> np.ndarray:
    return np.zeros(width * height * FILM_F, np.float32)


def initial_mask(width: int, height: int, region: tuple[int, int, int, int] | None = None) -> np.ndarray:
    """uint32 (H·W) 'active' mask: every pixel, or only those of the region (x0, y0, x1, y1; x1 ≤ x0: all)."""
    mask = np.ones((height, width), np.uint32)
    if region is not None and region[2] > region[0]:
        x0, y0, x1, y1 = region
        mask[:] = 0
        mask[max(0, y0) : max(0, y1), max(0, x0) : max(0, x1)] = 1
    return mask.ravel()


def _pixels(accum: np.ndarray, width: int, height: int) -> np.ndarray:
    return accum.reshape(height, width, FILM_F)


def film_image(accum: np.ndarray, width: int, height: int) -> np.ndarray:
    """float32 (H, W, 3): the mean radiance of every pixel."""
    a = _pixels(accum, width, height)
    image: np.ndarray = a[..., :3] / np.maximum(a[..., 3:4], 1.0)
    return image


def pixel_error(accum: np.ndarray, width: int, height: int) -> np.ndarray:
    """Relative error per pixel: |all − even| summed over RGB, over √(summed brightness) (0 = no samples)."""
    a = _pixels(accum, width, height)
    weight, even_weight = a[..., 3:4], a[..., 7:8]
    sampled = (weight[..., 0] > 0) & (even_weight[..., 0] > 0)
    full = a[..., :3] / np.maximum(weight, EPSILON)
    half = a[..., 4:7] / np.maximum(even_weight, EPSILON)
    diff = np.abs(full - half).sum(axis=-1)
    error = diff / (EPSILON + np.sqrt(np.maximum(full, 0.0).sum(axis=-1)))
    return np.where(sampled, error, 0.0).astype(np.float32)


def dilate(mask: np.ndarray, radius: int = 1) -> np.ndarray:
    """Grow a boolean mask by ``radius`` pixels (a square window), so noisy regions keep soft borders."""
    out = mask.copy()
    padded = np.pad(mask, radius)
    h, w = mask.shape
    for dy in range(2 * radius + 1):
        for dx in range(2 * radius + 1):
            out |= padded[dy : dy + h, dx : dx + w]
    return out


def active_mask(accum: np.ndarray, width: int, height: int, threshold: float) -> np.ndarray:
    """uint32 (H·W): 1 for pixels (and their neighbours) whose error is still above ``threshold``."""
    noisy = pixel_error(accum, width, height) > threshold
    return dilate(noisy).astype(np.uint32).ravel()
