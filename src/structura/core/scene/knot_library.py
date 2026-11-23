"""Curated knot library (KNOTS_TAB_PLAN Phase 0): the named knots of the future "Knots" dock panel.

A knot is a name plus one or more components; a component is a closed or open bead polyline with a tube radius
and a colour. Phase 0 fixes this catalogue format and seeds it with the first curated knots; the smooth-tube
geometry, the preview/render integration and the big catalogues land in later phases.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from functools import cache
from pathlib import Path

Vec3 = tuple[float, float, float]

KNOTS_FILE = Path(__file__).resolve().parent / "knot_library.toml"


@dataclass(frozen=True)
class KnotComponent:
    """One knot component: a bead polyline closed or open, with a tube radius and a colour.

    Attributes:
        beads: The bead positions in scene units, in the knot's own frame.
        closed: Whether the polyline closes into a loop.
        radius: The tube radius in scene units.
        rgba: The colour of the component as (red, green, blue, alpha).
    """

    beads: tuple[Vec3, ...]
    closed: bool
    radius: float
    rgba: tuple[float, ...]


@dataclass(frozen=True)
class Knot:
    """A named knot: one or more components (a knot may be a link of several of them).

    Attributes:
        name: The catalogue name.
        doc: One line on what the knot is.
        components: Its components in order.
    """

    name: str
    doc: str
    components: tuple[KnotComponent, ...]


@cache
def knots() -> dict[str, Knot]:
    """Returns every curated knot of knot_library.toml by name, in file order (read once).

    Returns:
        The curated knots keyed by name.

    Raises:
        ValueError: If a curated knot has no component or a component has no beads.
    """
    table = tomllib.loads(KNOTS_FILE.read_text(encoding="utf-8"))
    out: dict[str, Knot] = {}
    for entry in table["knot"]:
        name = str(entry["name"])
        components: tuple[KnotComponent, ...] = tuple(
            KnotComponent(
                beads=tuple((float(bead[0]), float(bead[1]), float(bead[2])) for bead in comp["beads"]),
                closed=bool(comp.get("closed", False)),
                radius=float(comp.get("radius", 0.0)),
                rgba=tuple(float(c) for c in comp.get("rgba", (0.8, 0.2, 0.2, 1.0))),
            )
            for comp in entry["components"]
        )
        if not components:
            raise ValueError(f"knot {name!r}: no components")
        for comp in components:
            if not comp.beads:
                raise ValueError(f"knot {name!r}: component without beads")
        out[name] = Knot(name=name, doc=str(entry.get("doc", "")), components=components)
    return out
