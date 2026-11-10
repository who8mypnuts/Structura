"""Lighting rigs (PLAN F3): complete lighting set-ups — lights and an environment — written into a v2 script
in one step, placed and sized for the structure (light_rigs.toml explains the units).

A rig's lights are named 'rig_…' and preceded by a marker comment; applying another rig removes them (and the
marker) first and replaces the environment block, so trying rigs one after the other never piles up lights.
The user's own lights stay. Everything written is ordinary v2 text the user can edit afterwards."""

from __future__ import annotations

import math
import re
import tomllib
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import numpy as np

from ..lang.v2.block_form import block_text
from .script_blocks import append_block, block_names, put_block, remove_block
from .vectors import as_vec3

RIGS_FILE = Path(__file__).resolve().parent / "light_rigs.toml"
PREFIX = "rig_"
MARKER = "// lighting rig: {name} (Structura; lights named rig_… are replaced when another rig is applied)"
MARKER_LINE = re.compile(r"(?m)^[ \t]*// lighting rig: [^\n]*\n?")


@dataclass(frozen=True)
class Rig:
    """A lighting rig as light_rigs.toml describes it.

    Attributes:
        name: The name shown in the Lights panel.
        doc: One sentence on the mood it makes.
        environment: The entries of its environment block.
        lights: Its light specifications (placement in bounding radii; see light_rigs.toml).
        look: The Render view look it is made for (render/post.py LOOKS), or "".
    """

    name: str
    doc: str
    environment: dict[str, Any]
    lights: tuple[dict[str, Any], ...]
    look: str = ""


@cache
def rigs() -> dict[str, Rig]:
    """Returns every rig of light_rigs.toml by name, in file order (read once)."""
    table = tomllib.loads(RIGS_FILE.read_text(encoding="utf-8"))
    return {
        r["name"]: Rig(r["name"], r["doc"], dict(r["environment"]), tuple(r.get("light", ())), r.get("look", ""))
        for r in table["rig"]
    }


def _sun_entries(spec: dict[str, Any]) -> dict[str, Any]:
    """A sun: its direction and angle as given; the irradiance is its intensity."""
    out: dict[str, Any] = {k: as_vec3(spec[k]) if k == "direction" else float(spec[k])
                           for k in ("direction", "angle") if k in spec}  # fmt: skip
    return out | {"intensity": float(spec.get("irradiance", 1.0))}


def _placed_entries(spec: dict[str, Any], centre: np.ndarray, radius: float) -> dict[str, Any]:
    """A positioned light facing ``centre``, its power chosen for the irradiance it should give there."""
    kind = spec["type"]
    position = centre + np.asarray(spec["at"], np.float64) * radius
    distance = float(np.linalg.norm(position - centre))
    out: dict[str, Any] = {"position": as_vec3(position)}
    if kind in ("spot", "rect"):
        out["target"] = as_vec3(centre)
    if kind == "rect":
        out["size"] = tuple(float(v) * radius for v in spec["size"])
    if kind == "sphere":
        out["radius"] = float(spec["radius"]) * radius
    if kind == "spot":
        out |= {k: float(spec[k]) for k in ("cone", "blend") if k in spec}
    # point, sphere and spot radiate P/4π per steradian; a rect radiates P/π along its normal (render/lights.py)
    out["power"] = float(spec.get("irradiance", 1.0)) * distance**2 * (math.pi if kind == "rect" else 4 * math.pi)
    return out


def light_entries(spec: dict[str, Any], lo: np.ndarray, hi: np.ndarray) -> dict[str, Any]:
    """Places one rig light for a structure.

    Args:
        spec: The light's table from light_rigs.toml.
        lo: The structure's bounding-box minimum.
        hi: The structure's bounding-box maximum.

    Returns:
        The entries of its light block (type first, colour last).
    """
    lo, hi = np.asarray(lo, np.float64), np.asarray(hi, np.float64)
    centre, radius = (lo + hi) / 2, max(float(np.linalg.norm(hi - lo)) / 2, 1e-3)
    kind = spec["type"]
    body = _sun_entries(spec) if kind == "sun" else _placed_entries(spec, centre, radius)
    return {"type": kind, **body, "color": spec.get("color", "#ffffff")}


def remove_rig(text: str) -> str:
    """Removes the lights and the marker comment of a rig applied earlier.

    Args:
        text: The script.

    Returns:
        The script without them (the user's own lights stay).
    """
    for name in sorted(block_names(text, "light")):
        if name.startswith(PREFIX):
            text = remove_block(text, "light", name)
    return MARKER_LINE.sub("", text)


def apply_rig(text: str, rig: Rig, lo: np.ndarray, hi: np.ndarray) -> str:
    """Lights a script with a rig.

    Earlier rig lights are removed, the rig's lights are added after the other declarations (behind a marker
    comment), and the environment block is replaced. The user's own lights stay.

    Args:
        text: The v2 script.
        rig: The rig to apply (light_rigs.toml).
        lo: The structure's bounding-box minimum.
        hi: The structure's bounding-box maximum.

    Returns:
        The new script text.
    """
    text = put_block(remove_rig(text), "environment", "", block_text("environment", "", rig.environment))
    blocks = [block_text("light", PREFIX + spec["name"], light_entries(spec, lo, hi)) for spec in rig.lights]
    return append_block(text, "\n".join([MARKER.format(name=rig.name), *blocks])) if blocks else text
