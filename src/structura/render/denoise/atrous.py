"""Edge-avoiding À-Trous wavelet denoising (Dammertz et al. 2010), the always-available denoiser.

Five passes of a 5×5 B3-spline kernel with holes (step 1, 2, 4, 8, 16). Each tap is weighted by how similar
its colour, normal and albedo are to the centre pixel, so edges and texture stay sharp. The albedo is only a
guide (no demodulation): glossy highlights are not proportional to albedo, and dividing by a saturated albedo
such as pure green would blow up the other channels.
"""

from __future__ import annotations

import math

import numpy as np
from numba import prange

from ...core.jit import kernel, parallel_kernel, parallel_section

PASSES = 5
SIGMA_COLOR, SIGMA_NORMAL, SIGMA_ALBEDO = 0.6, 0.15, 0.1
KERNEL = np.array([1 / 16, 1 / 4, 3 / 8, 1 / 4, 1 / 16], np.float32)


@kernel
def _tap_weight(  # noqa: PLR0913, PLR0917 - a scalar inner-loop helper of a Numba kernel
    src: np.ndarray, normal: np.ndarray, albedo: np.ndarray, y: int, x: int, yy: int, xx: int, inv_c: float
) -> float:
    """Edge-stopping weight of tap (yy, xx) for the centre (y, x)."""
    dc = dn = da = 0.0
    for c in range(3):
        dc += (src[yy, xx, c] - src[y, x, c]) ** 2
        dn += (normal[yy, xx, c] - normal[y, x, c]) ** 2
        da += (albedo[yy, xx, c] - albedo[y, x, c]) ** 2
    return math.exp(-dc * inv_c - dn / SIGMA_NORMAL**2 - da / SIGMA_ALBEDO**2)


@parallel_kernel
def _pass(
    src: np.ndarray, normal: np.ndarray, albedo: np.ndarray, step: int, sigma_c: float, taps: np.ndarray
) -> np.ndarray:
    h, w, _ = src.shape
    out = np.empty_like(src)
    inv_c = 1.0 / (sigma_c * sigma_c)
    for y in prange(h):
        for x in range(w):
            acc0 = acc1 = acc2 = weights = 0.0
            for j in range(5):
                yy = min(max(y + (j - 2) * step, 0), h - 1)
                for i in range(5):
                    xx = min(max(x + (i - 2) * step, 0), w - 1)
                    wgt = taps[j] * taps[i] * _tap_weight(src, normal, albedo, y, x, yy, xx, inv_c)
                    acc0 += wgt * src[yy, xx, 0]
                    acc1 += wgt * src[yy, xx, 1]
                    acc2 += wgt * src[yy, xx, 2]
                    weights += wgt
            out[y, x, 0] = acc0 / weights
            out[y, x, 1] = acc1 / weights
            out[y, x, 2] = acc2 / weights
    return out


def atrous_denoise(image: np.ndarray, albedo: np.ndarray | None = None, normal: np.ndarray | None = None) -> np.ndarray:
    img = np.ascontiguousarray(image, np.float32)
    alb = np.ascontiguousarray(albedo if albedo is not None else np.zeros_like(img), np.float32)
    nrm = np.ascontiguousarray(normal if normal is not None else np.zeros_like(img), np.float32)
    # compress the dynamic range for the colour weights (fireflies must not dominate the similarity)
    scale = float(np.median(img[img > 0])) if np.any(img > 0) else 1.0
    current = np.ascontiguousarray(img / max(scale, 1e-6), np.float32)
    for k in range(PASSES):
        with parallel_section():
            current = _pass(current, nrm, alb, 1 << k, SIGMA_COLOR * 2.0 ** (-k), KERNEL)
    out: np.ndarray = (current * scale).astype(np.float32)
    return out
