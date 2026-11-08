"""Colour-by modes for the viewport (docs/08 §5): show the structure coloured by how it was made instead of
its authored colours. Renders and exports always use the authored colours.

Ramps and palettes are colour-blind safe (docs/14 §8): generations use cividis; categories (call sites,
tags, kinds) use the Okabe–Ito palette, extended by lightness steps when there are more categories.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from .ir import SceneIR

MODES = ("authored", "generation", "call site", "tag", "kind", "random")
OKABE_ITO = np.array([[230, 159, 0], [86, 180, 233], [0, 158, 115], [240, 228, 66], [0, 114, 178],
                      [213, 94, 0], [204, 121, 167], [153, 153, 153]], np.float32) / 255.0  # fmt: skip
CIVIDIS = np.array([[0.000, 0.135, 0.304], [0.173, 0.247, 0.420], [0.320, 0.340, 0.420], [0.451, 0.443, 0.451],
                    [0.580, 0.549, 0.471], [0.722, 0.659, 0.447], [0.867, 0.776, 0.380], [0.996, 0.910, 0.220]],
                   np.float32)  # fmt: skip


def cividis(t: np.ndarray) -> np.ndarray:
    """float[N] in [0, 1] → sRGB float[N, 3] along the cividis ramp."""
    x = np.clip(t, 0.0, 1.0) * (len(CIVIDIS) - 1)
    i = np.minimum(x.astype(np.int64), len(CIVIDIS) - 2)
    f = (x - i)[:, None]
    out: np.ndarray = CIVIDIS[i] * (1 - f) + CIVIDIS[i + 1] * f
    return out


def categorical(keys: np.ndarray) -> np.ndarray:
    """Integer categories → distinct sRGB colours (Okabe–Ito, then lighter and darker rounds)."""
    _, index = np.unique(keys, return_inverse=True)
    base = OKABE_ITO[index % len(OKABE_ITO)]
    shade = (index // len(OKABE_ITO)) % 3  # 0: as is, 1: lighter, 2: darker
    lighter, darker = base + (1 - base) * 0.45, base * 0.6
    out: np.ndarray = np.where((shade == 1)[:, None], lighter, np.where((shade == 2)[:, None], darker, base))
    return out


def _hash(values: np.ndarray) -> np.ndarray:
    x = values.astype(np.uint64) * np.uint64(0x9E3779B97F4A7C15)
    return (x >> np.uint64(40)).astype(np.float64) / float(1 << 24)


def colors_for(scene: SceneIR, mode: str) -> np.ndarray:
    """sRGB float[N, 3] for ``mode`` (see MODES)."""
    n = len(scene)
    if mode == "generation":
        top = max(1, int(scene.generation.max(initial=0)))
        return cividis(scene.generation / top)
    if mode in ("call site", "tag", "kind"):
        column = {"call site": scene.source, "tag": scene.tag, "kind": scene.kind}[mode]
        return categorical(np.asarray(column, np.int64))
    if mode == "random":
        rows = np.arange(n)
        channels = [0.35 + 0.6 * _hash(rows + k * n) for k in range(3)]
        return np.stack(channels, axis=1).astype(np.float32)
    return np.asarray(scene.rgba[:, :3])


def recolored(scene: SceneIR, mode: str) -> SceneIR:
    """``scene`` with its colours replaced for ``mode`` (alpha kept); the same scene for 'authored'."""
    if mode == "authored" or mode not in MODES or not len(scene):
        return scene
    rgba = np.array(scene.rgba, np.float32)
    rgba[:, :3] = colors_for(scene, mode)
    return replace(scene, rgba=rgba)
