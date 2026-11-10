"""3D colour look-up tables in the Adobe / Resolve '.cube' format (the post stack's grading LUT; PLAN F1).

A LUT maps display colours (0..1) to display colours; it is applied with trilinear interpolation. Files are read
once and cached by path and modification time."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np


def parse_cube(text: str) -> np.ndarray:
    """float32 (N, N, N, 3) indexed [b, g, r] as the format orders it (red changes fastest)."""
    size, domain_min, domain_max, rows = 0, np.zeros(3), np.ones(3), []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("TITLE"):
            continue
        head, *rest = line.split()
        if head == "LUT_3D_SIZE":
            size = int(rest[0])
        elif head == "DOMAIN_MIN":
            domain_min = np.array([float(v) for v in rest])
        elif head == "DOMAIN_MAX":
            domain_max = np.array([float(v) for v in rest])
        elif head[0].isdigit() or head[0] in "-.":
            rows.append([float(head), *(float(v) for v in rest[:2])])
    if size < 2 or len(rows) != size**3:
        raise ValueError(f"not a 3D .cube LUT (size {size}, {len(rows)} entries)")
    if not (np.allclose(domain_min, 0.0) and np.allclose(domain_max, 1.0)):
        raise ValueError("only .cube LUTs with the 0..1 domain are supported")
    return np.asarray(rows, np.float32).reshape(size, size, size, 3)


@lru_cache(maxsize=8)
def _load(path: str, mtime: float) -> np.ndarray:
    return parse_cube(Path(path).read_text(encoding="utf-8", errors="replace"))


def load_cube(path: Path) -> np.ndarray:
    return _load(str(path), path.stat().st_mtime)


def apply_lut(rgb: np.ndarray, lut: np.ndarray) -> np.ndarray:
    """Map display colours ``rgb`` (float 0..1, any shape ending in 3) through the table, trilinearly."""
    n = lut.shape[0]
    x = np.clip(rgb, 0.0, 1.0) * (n - 1)
    i0 = np.minimum(x.astype(np.int32), n - 2)
    f = x - i0
    r0, g0, b0 = i0[..., 0], i0[..., 1], i0[..., 2]
    fr, fg, fb = f[..., 0:1], f[..., 1:2], f[..., 2:3]
    out = np.zeros(rgb.shape, np.float32)
    for db, wb in ((0, 1 - fb), (1, fb)):
        for dg, wg in ((0, 1 - fg), (1, fg)):
            for dr, wr in ((0, 1 - fr), (1, fr)):
                out += lut[b0 + db, g0 + dg, r0 + dr] * (wb * wg * wr)
    return out
