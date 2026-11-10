"""3D colour look-up tables in the Adobe / Resolve '.cube' format (the post stack's grading LUT; PLAN F1).

A LUT maps display colours (0..1) to display colours; it is applied with trilinear interpolation. Files are read
once and cached by path and modification time."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np


def parse_cube(text: str) -> np.ndarray:
    """Reads a 3D look-up table in the '.cube' format.

    Args:
        text: The file's text.

    Returns:
        float32 (N, N, N, 3), indexed [b, g, r] as the format orders it (red changes fastest).

    Raises:
        ValueError: Not a 3D table of N³ entries, or a domain other than 0..1.
    """
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
    """Returns the table of a '.cube' file, cached by path and modification time.

    Args:
        path: The file.

    Raises:
        OSError: The file cannot be read.
        ValueError: It is not a usable table (see ``parse_cube``).
    """
    return _load(str(path), path.stat().st_mtime)


def apply_lut(rgb: np.ndarray, lut: np.ndarray) -> np.ndarray:
    """Maps display colours through a table, interpolating trilinearly.

    Args:
        rgb: float display colours (clamped to 0..1; NaN reads as 0), any shape ending in 3.
        lut: A table from ``parse_cube``.

    Returns:
        float32 colours of the same shape.
    """
    n = lut.shape[0]
    x = np.clip(np.nan_to_num(rgb, nan=0.0), 0.0, 1.0) * (n - 1)  # (a NaN pixel must not index the table)
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
