"""New v2 'light' blocks placed sensibly around a structure (docs/05 §9.4, docs/14 §3 Environment & Lights).

Positions and power follow the bounding box, so a light added to a tiny or a huge structure is visible at
once; the user then edits the numbers in the script."""

from __future__ import annotations

import numpy as np

KINDS = ("sun", "point", "sphere", "spot", "rect")


def _v(values: np.ndarray) -> str:
    return "[" + " ".join(f"{float(c):.4g}" for c in values) + "]"


def light_text(kind: str, name: str, lo: np.ndarray, hi: np.ndarray) -> str:
    lo, hi = np.asarray(lo, np.float64), np.asarray(hi, np.float64)
    centre, radius = (lo + hi) / 2, max(float(np.linalg.norm(hi - lo)) / 2, 1e-3)
    above = centre + np.array([0.6, 1.6, 0.9]) * radius
    power = f"{40.0 * radius * radius:.4g}"  # irradiance at the structure independent of its size
    body = {
        "sun": ["type sun", "direction [-0.4 -0.8 -0.45]", "intensity 1", "angle 2", "color #fff4e0"],
        "point": ["type point", f"position {_v(above)}", f"power {power}", "color #ffffff"],
        "sphere": [
            "type sphere",
            f"position {_v(above)}",
            f"radius {radius * 0.15:.4g}",
            f"power {power}",
            "color #ffffff",
        ],
        "spot": [
            "type spot",
            f"position {_v(above)}",
            f"target {_v(centre)}",
            "cone 25",
            "blend 0.2",
            f"power {power}",
            "color #ffffff",
        ],
        "rect": [
            "type rect",
            f"position {_v(centre + np.array([0.0, 1.8, 0.0]) * radius)}",
            f"target {_v(centre)}",
            f"size [{radius:.4g} {radius:.4g}]",
            f"power {power}",
            "color #ffffff",
        ],
    }[kind]
    return "\n".join([f"light {name} {{", *(f"  {line}" for line in body), "}"])


def free_name(kind: str, taken: set[str]) -> str:
    n = 1
    while f"{kind}{n}" in taken:
        n += 1
    return f"{kind}{n}"
