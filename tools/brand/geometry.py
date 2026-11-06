"""Geometry of the Structura mark: a chain of isometric cubes shrinking along an 'S'.

The construction mirrors an EisenScript rule: every cube spawns a smaller successor a little further along
the curve (``rule R { { x 1 rz 15 s 0.9 } R box }``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import pairwise

Point = tuple[float, float]
COS30 = math.cos(math.radians(30))


@dataclass(frozen=True)
class Cube:
    center: Point
    size: float  # hexagon "radius"
    t: float  # position along the chain, 0 = first (largest) cube

    def faces(self) -> dict[str, list[Point]]:
        cx, cy = self.center
        s = self.size
        top, bottom = (cx, cy - s), (cx, cy + s)
        ur, lr = (cx + s * COS30, cy - s / 2), (cx + s * COS30, cy + s / 2)
        ul, ll = (cx - s * COS30, cy - s / 2), (cx - s * COS30, cy + s / 2)
        c = (cx, cy)
        return {"top": [top, ur, c, ul], "left": [ul, c, bottom, ll], "right": [c, ur, lr, bottom]}


def s_curve_point(u: float, radius: float) -> Point:
    """Point on the S centerline, u in [0, 1] from the bottom-left tail to the top-right head (y down)."""
    lower_sweep, upper_sweep = 250.0, 250.0
    span = lower_sweep + upper_sweep
    a = u * span
    if a <= lower_sweep:  # lower bowl: centre (0, -R) in y-up coordinates, clockwise from -160 deg to 90 deg
        ang = math.radians(-160.0 + a)
        x, y = radius * math.cos(ang), -radius + radius * math.sin(ang)
    else:  # upper bowl: centre (0, R), counter-clockwise from 270 deg, ending top-right
        ang = math.radians(270.0 - (a - lower_sweep))
        x, y = radius * math.cos(ang), radius + radius * math.sin(ang)
    return (x, -y)


def arc_length_table(radius: float, samples: int = 2000) -> list[tuple[float, Point]]:
    pts = [s_curve_point(i / samples, radius) for i in range(samples + 1)]
    table, acc = [(0.0, pts[0])], 0.0
    for p, q in pairwise(pts):
        acc += math.dist(p, q)
        table.append((acc, q))
    return table


def point_at_length(table: list[tuple[float, Point]], length: float) -> Point:
    lo, hi = 0, len(table) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if table[mid][0] < length:
            lo = mid + 1
        else:
            hi = mid
    return table[lo][1]


def cube_chain(count: int, ratio: float, radius: float, spacing: float = 1.05, size_factor: float = 0.62) -> list[Cube]:
    """Cubes with geometric sizes placed by arc length so neighbours just overlap."""
    table = arc_length_table(radius)
    total = table[-1][0]
    weights = [ratio**i for i in range(count)]
    unit = total / (spacing * (sum(weights) - weights[0] / 2 - weights[-1] / 2))
    cubes, pos = [], 0.0
    for i, w in enumerate(weights):
        if i:
            pos += spacing * unit * (weights[i - 1] + w) / 2
        size = unit * w * size_factor
        cubes.append(Cube(point_at_length(table, pos), size, i / max(1, count - 1)))
    return cubes
