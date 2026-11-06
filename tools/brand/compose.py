"""Compose the brand assets (marks, app icon, lockups) from geometry + wordmark."""

from __future__ import annotations

from .geometry import Cube, cube_chain
from .svg import bounds, document, mark_body
from .wordmark import text_path

BG_TOP, BG_BOTTOM = "#0B1022", "#1C1642"
INK_DARK_BG, INK_LIGHT_BG = "#E8ECF4", "#0F172A"
PRIMARY = {"count": 22, "ratio": 0.92, "radius": 100.0, "spacing": 0.97}
COMPACT = {"count": 20, "ratio": 0.97, "radius": 100.0, "spacing": 0.70, "size_factor": 0.46}

View = tuple[float, float, float, float]


def primary_cubes() -> list[Cube]:
    return cube_chain(**PRIMARY)  # type: ignore[arg-type]


def compact_cubes() -> list[Cube]:
    return cube_chain(**COMPACT)  # type: ignore[arg-type]


def fit_group(body: str, view: View, box: View) -> str:
    """Uniformly scale+translate ``body`` (in ``view`` coordinates) into ``box``, centred."""
    vx0, vy0, vx1, vy1 = view
    bx0, by0, bx1, by1 = box
    s = min((bx1 - bx0) / (vx1 - vx0), (by1 - by0) / (vy1 - vy0))
    tx = bx0 + ((bx1 - bx0) - s * (vx1 - vx0)) / 2 - s * vx0
    ty = by0 + ((by1 - by0) - s * (vy1 - vy0)) / 2 - s * vy0
    return f'<g transform="translate({tx:.3f} {ty:.3f}) scale({s:.5f})">{body}</g>'


def mark_svg(compact: bool = False, size: int = 1024) -> str:
    cubes = compact_cubes() if compact else primary_cubes()
    stroke = None
    return document(bounds(cubes, 6), mark_body(cubes, stroke), (size, size))


def icon_svg(compact: bool = False, size: int = 1024) -> str:
    defs = (
        f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{BG_TOP}"/><stop offset="1" stop-color="{BG_BOTTOM}"/></linearGradient>'
        '<radialGradient id="glow" cx="0.5" cy="0.55" r="0.5">'
        '<stop offset="0" stop-color="#3B82F6" stop-opacity="0.38"/>'
        '<stop offset="1" stop-color="#3B82F6" stop-opacity="0"/></radialGradient>'
        '<radialGradient id="shadow" cx="0.5" cy="0.5" r="0.5">'
        '<stop offset="0" stop-color="#000000" stop-opacity="0.45"/>'
        '<stop offset="1" stop-color="#000000" stop-opacity="0"/></radialGradient>'
    )
    cubes = compact_cubes() if compact else primary_cubes()
    stroke = BG_BOTTOM if compact else None
    inner = mark_body(cubes, stroke, 0.10)
    box = (120.0, 86.0, 904.0, 910.0) if not compact else (100.0, 80.0, 924.0, 944.0)
    body = (
        '<rect x="0" y="0" width="1024" height="1024" rx="228" fill="url(#bg)"/>'
        '<rect x="0" y="0" width="1024" height="1024" rx="228" fill="url(#glow)"/>'
        '<rect x="6" y="6" width="1012" height="1012" rx="222" fill="none" '
        'stroke="#FFFFFF" stroke-opacity="0.08" stroke-width="4"/>'
        f'<ellipse cx="512" cy="{box[3] - 18:.0f}" rx="300" ry="54" fill="url(#shadow)"/>'
        + fit_group(inner, bounds(cubes, 4), box)
    )
    return document((0, 0, 1024, 1024), body, (size, size), defs)


def lockup_svg(ink: str, height: int = 256) -> str:
    """Horizontal lockup: mark + 'Structura' wordmark. ``ink`` is the text colour."""
    text = text_path("Structura", 100.0, weight=700, tracking=-0.015)
    mark_h = text.cap_height * 1.9
    cubes = primary_cubes()
    mark = fit_group(mark_body(cubes), bounds(cubes, 2), (0.0, -mark_h / 2, mark_h, mark_h / 2))
    gap = mark_h * 0.22
    baseline = text.cap_height / 2
    word = f'<path transform="translate({mark_h + gap:.2f} {baseline:.2f})" d="{text.d}" fill="{ink}"/>'
    pad = mark_h * 0.12
    width = mark_h + gap + text.width
    view = (-pad, -mark_h / 2 - pad, width + pad, mark_h / 2 + pad)
    aspect = (view[2] - view[0]) / (view[3] - view[1])
    return document(view, mark + word, (round(height * aspect), height))
