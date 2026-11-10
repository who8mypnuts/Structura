"""3-vectors as they travel between scripts, settings, files and text: one place for reading a vector value,
turning an array into plain floats, and writing vectors for people (reports, panels) or for scripts."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, overload

Vec3 = tuple[float, float, float]


@overload
def vec3_of(value: Any) -> Vec3 | None: ...
@overload
def vec3_of(value: Any, default: Vec3) -> Vec3: ...
def vec3_of(value: Any, default: Vec3 | None = None) -> Vec3 | None:
    """``value`` as three floats when it is a 3-sequence of numbers (tuple, list, array), else ``default``."""
    if isinstance(value, str | bytes):
        return default
    try:
        if len(value) == 3:
            x, y, z = (float(c) for c in value)
            return (x, y, z)
    except (TypeError, ValueError):
        pass
    return default


def as_vec3(v: Any) -> Vec3:
    """The first three components of an array or sequence as plain floats."""
    return (float(v[0]), float(v[1]), float(v[2]))


def number(x: float, spec: str = ".6g") -> str:
    """``x`` formatted with ``spec``; a negative zero prints as zero ('-0', '-0.000' → '0', '0.000')."""
    text = format(float(x), spec)
    return text[1:] if text.startswith("-") and float(text) == 0.0 else text


def fmt_vec(v: Iterable[float], spec: str = ".4g") -> str:
    """'(x, y, z)' for people: reports, panels and status messages."""
    return "(" + ", ".join(number(c, spec) for c in v) + ")"


def script_vec(v: Iterable[float], spec: str = ".6g") -> str:
    """'[x y z]' as EisenScript v2 blocks write vectors."""
    return "[" + " ".join(number(c, spec) for c in v) + "]"
