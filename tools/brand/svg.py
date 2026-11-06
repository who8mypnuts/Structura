"""SVG assembly for the Structura mark, icon and lockups."""

from __future__ import annotations

from .color import gradient, mix
from .geometry import Cube, Point

PALETTE = ["#22D3EE", "#3B82F6", "#8B5CF6", "#EC4899"]  # cyan → blue → violet → pink


def _poly(points: list[Point], fill: str, extra: str = "") -> str:
    pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return f'<polygon points="{pts}" fill="{fill}"{extra}/>'


def cube_svg(cube: Cube, stroke: str | None, stroke_w: float) -> str:
    base = gradient(PALETTE, cube.t)
    shades = {"top": mix(base, "#FFFFFF", 0.38), "left": base, "right": mix(base, "#000000", 0.30)}
    extra = ""
    if stroke:
        extra = f' stroke="{stroke}" stroke-width="{stroke_w * cube.size:.2f}" stroke-linejoin="round"'
    return "".join(_poly(face, shades[name], extra) for name, face in cube.faces().items())


def paint_order(cubes: list[Cube]) -> list[Cube]:
    """Back to front: smaller (younger) cubes sit behind their larger parents."""
    return sorted(cubes, key=lambda c: -c.t)


def bounds(cubes: list[Cube], pad: float, square: bool = True) -> tuple[float, float, float, float]:
    xs = [p[0] for c in cubes for f in c.faces().values() for p in f]
    ys = [p[1] for c in cubes for f in c.faces().values() for p in f]
    x0, y0, x1, y1 = min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad
    if square:
        side = max(x1 - x0, y1 - y0)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        x0, y0, x1, y1 = cx - side / 2, cy - side / 2, cx + side / 2, cy + side / 2
    return (x0, y0, x1, y1)


def mark_body(cubes: list[Cube], stroke: str | None = None, stroke_w: float = 0.06) -> str:
    return "\n".join(cube_svg(c, stroke, stroke_w) for c in paint_order(cubes))


def document(view: tuple[float, float, float, float], body: str, size: tuple[int, int], defs: str = "") -> str:
    x0, y0, x1, y1 = view
    w, h = size
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="{x0:.2f} {y0:.2f} {x1 - x0:.2f} {y1 - y0:.2f}">\n'
        f"<defs>{defs}</defs>\n{body}\n</svg>\n"
    )
