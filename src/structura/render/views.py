"""View transforms (docs/09 §7): scene-linear radiance → display-linear values in [0, 1] (sRGB primaries),
before the sRGB encoding. 'standard' clips (Structure Synth's look), 'soft' rolls highlights off, 'agx' is
the AgX base look (the default for physically based renders), 'aces' the fitted ACES RRT+ODT and 'filmic'
the Hable curve."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)
AGX_INSET = np.array([[0.842479062253094, 0.0423282422610123, 0.0423756549057051],
                      [0.0784335999999992, 0.878468636469772, 0.0784336],
                      [0.0792237451477643, 0.0791661274605434, 0.879142973793104]])  # fmt: skip
AGX_OUTSET = np.array([[1.19687900512017, -0.0528968517574562, -0.0529716355144438],
                       [-0.0980208811401368, 1.15190312990417, -0.0980434501171241],
                       [-0.0990297440797205, -0.0989611768448433, 1.15107367264116]])  # fmt: skip
AGX_MIN_EV, AGX_MAX_EV = -12.47393, 4.026069
ACES_IN = np.array([[0.59719, 0.35458, 0.04823], [0.07600, 0.90834, 0.01566], [0.02840, 0.13383, 0.83777]])
ACES_OUT = np.array([[1.60475, -0.53108, -0.07367], [-0.10208, 1.10813, -0.00605], [-0.00327, -0.07276, 1.07602]])


def _unit(v: np.ndarray) -> np.ndarray:
    out: np.ndarray = np.clip(v, 0.0, 1.0)
    return out


def standard(rgb: np.ndarray) -> np.ndarray:
    return _unit(rgb)


def soft(rgb: np.ndarray) -> np.ndarray:
    """Gentle highlight roll-off: Reinhard on luminance above 0.8, hue preserved."""
    lum = rgb @ LUMA
    over = np.maximum(lum - 0.8, 0.0)
    knee = np.where(lum > 0.8, 0.8 + over / (1.0 + over / 0.6), lum)
    return _unit(rgb * (knee / np.maximum(lum, 1e-8))[..., None])


def agx(rgb: np.ndarray) -> np.ndarray:
    """AgX base (Sobotka): inset matrix, log2 encoding over 16.5 stops, sigmoid, outset, display gamma 2.2."""
    v = np.maximum(rgb @ AGX_INSET, 1e-10)
    v = (np.clip(np.log2(v), AGX_MIN_EV, AGX_MAX_EV) - AGX_MIN_EV) / (AGX_MAX_EV - AGX_MIN_EV)
    v2 = v * v
    v4 = v2 * v2
    v = 15.5 * v4 * v2 - 40.14 * v4 * v + 31.96 * v4 - 6.868 * v2 * v + 0.4298 * v2 + 0.1191 * v - 0.00232
    return _unit(_unit(v @ AGX_OUTSET) ** 2.2)


def aces(rgb: np.ndarray) -> np.ndarray:
    """The fitted ACES RRT + ODT (Hill)."""
    v = rgb @ ACES_IN.T
    v = (v * (v + 0.0245786) - 0.000090537) / (v * (0.983729 * v + 0.4329510) + 0.238081)
    return _unit(v @ ACES_OUT.T)


def _hable(x: np.ndarray) -> np.ndarray:
    a, b, c, d, e, f = 0.15, 0.50, 0.10, 0.20, 0.02, 0.30
    return (x * (a * x + c * b) + d * e) / (x * (a * x + b) + d * f) - e / f


def filmic(rgb: np.ndarray) -> np.ndarray:
    """Hable's filmic curve (white point 11.2), applied per channel."""
    return _unit(_hable(np.maximum(rgb, 0.0) * 2.0) / _hable(np.array(11.2)))


VIEW_TRANSFORMS: dict[str, Callable[[np.ndarray], np.ndarray]] = {
    "standard": standard, "soft": soft, "agx": agx, "aces": aces, "filmic": filmic,
}  # fmt: skip
