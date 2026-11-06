"""Denoising of path-traced images (docs/09 §7): Open Image Denoise when its library is available, else an
edge-avoiding À-Trous wavelet filter guided by the albedo and normal AOVs."""

from __future__ import annotations

import logging

import numpy as np

from ..aovs import Aovs
from .atrous import atrous_denoise
from .oidn import OidnUnavailableError, oidn_denoise

log = logging.getLogger(__name__)
METHODS = ("auto", "oidn", "atrous")


def denoise(
    image: np.ndarray, albedo: np.ndarray | None = None, normal: np.ndarray | None = None, method: str = "auto"
) -> tuple[np.ndarray, str]:
    """(denoised image, method used). 'auto' prefers OIDN and falls back to À-Trous."""
    if method in ("auto", "oidn"):
        try:
            return oidn_denoise(image, albedo, normal), "oidn"
        except OidnUnavailableError as exc:
            if method == "oidn":
                raise
            log.info("Open Image Denoise unavailable (%s); using the À-Trous filter", exc)
    return atrous_denoise(image, albedo, normal), "atrous"


def denoise_with(image: np.ndarray, aovs: Aovs | None, method: str = "auto") -> tuple[np.ndarray, str]:
    """``denoise`` guided by a render's AOVs when it has them."""
    if aovs is None:
        return denoise(image, method=method)
    return denoise(image, aovs.albedo, aovs.normal, method)
