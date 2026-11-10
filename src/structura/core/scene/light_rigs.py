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

RIGS_FILE = Path(__file__).resolve().parent / "light_rigs.toml"
PREFIX = "rig_"
MARKER = "// lighting rig: {name} (Structura; lights named rig_… are replaced when another rig is applied)"
MARKER_LINE = re.compile(r"(?m)^[ \t]*// lighting rig: [^\n]*\n?")


@dataclass(frozen=True)
class Rig:
    name: str
    doc: str
    environment: dict[str, Any]
    lights: tuple[dict[str, Any], ...]
    look: str = ""  # the Render tool bar look it is made for (render/post.py LOOKS)


@cache
def rigs() -> dict[str, Rig]:
    table = tomllib.loads(RIGS_FILE.read_text(encoding="utf-8"))
    return {
        r["name"]: Rig(r["name"], r["doc"], dict(r["environment"]), tuple(r.get("light", ())), r.get("look", ""))
        for r in table["rig"]
    }


def _value(value: Any) -> Any:
    """A TOML value as parse_body reads a script value (lists → tuples of floats)."""
    return tuple(float(v) for v in value) if isinstance(value, list) else value


def light_entries(spec: dict[str, Any], lo: np.ndarray, hi: np.ndarray) -> dict[str, Any]:
    """A rig light placed for the bounding box (lo, hi): the entries of its light block."""
    centre, radius = (lo + hi) / 2, max(float(np.linalg.norm(hi - lo)) / 2, 1e-3)
    kind, e = spec["type"], float(spec.get("irradiance", 1.0))
    out: dict[str, Any] = {"type": kind}
    if kind == "sun":
        out |= {k: _value(spec[k]) for k in ("direction", "angle") if k in spec} | {"intensity": e}
    else:
        position = centre + np.asarray(spec["at"], np.float64) * radius
        distance = float(np.linalg.norm(position - centre))
        out["position"] = tuple(float(v) for v in position)
        if kind in ("spot", "rect"):
            out["target"] = tuple(float(v) for v in centre)
        if kind == "rect":
            out["size"] = tuple(float(v) * radius for v in spec["size"])
        if kind == "sphere":
            out["radius"] = float(spec["radius"]) * radius
        if kind == "spot":
            out |= {k: float(spec[k]) for k in ("cone", "blend") if k in spec}
        # point, sphere, spot radiate P/4π per steradian; a rect P/π towards its normal (render/lights.py)
        out["power"] = e * distance * distance * (math.pi if kind == "rect" else 4 * math.pi)
    out["color"] = spec.get("color", "#ffffff")
    return out


def remove_rig(text: str) -> str:
    """``text`` without the lights and marker of a rig applied earlier."""
    for name in sorted(block_names(text, "light")):
        if name.startswith(PREFIX):
            text = remove_block(text, "light", name)
    return MARKER_LINE.sub("", text)


def apply_rig(text: str, rig: Rig, lo: np.ndarray, hi: np.ndarray) -> str:
    """``text`` lit by ``rig``: earlier rig lights removed, the rig's lights added, the environment replaced."""
    lo, hi = np.asarray(lo, np.float64), np.asarray(hi, np.float64)
    text = put_block(remove_rig(text), "environment", "", block_text("environment", "", rig.environment))
    blocks = [block_text("light", PREFIX + spec["name"], light_entries(spec, lo, hi)) for spec in rig.lights]
    return append_block(text, "\n".join([MARKER.format(name=rig.name), *blocks])) if blocks else text
