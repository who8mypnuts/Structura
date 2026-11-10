"""3-vectors as they travel between scripts, settings, files and text: one place for reading a vector value,
turning an array into plain floats, writing vectors for people (reports, panels) or for scripts, and turning
one about an axis."""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any, overload

import numpy as np

Vec3 = tuple[float, float, float]


@overload
def vec3_of(value: Any) -> Vec3 | None: ...
@overload
def vec3_of(value: Any, default: Vec3) -> Vec3: ...
def vec3_of(value: Any, default: Vec3 | None = None) -> Vec3 | None:
    """Reads a 3-vector.

    Args:
        value: A tuple, list or array of three numbers (anything else, strings included, is not a vector).
        default: What to return when ``value`` is not a vector.

    Returns:
        The three components as floats, or ``default``.
    """
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
    """Returns the first three components of an array or sequence as plain floats.

    Args:
        v: An array or sequence of at least three numbers.
    """
    return (float(v[0]), float(v[1]), float(v[2]))


def number(x: float, spec: str = ".6g") -> str:
    """Formats a number; a negative zero prints as zero ('-0', '-0.000' become '0', '0.000').

    Args:
        x: The number.
        spec: A format specification.

    Returns:
        The text.
    """
    text = format(float(x), spec)
    return text[1:] if text.startswith("-") and float(text) == 0.0 else text


def fmt_vec(v: Iterable[float], spec: str = ".4g") -> str:
    """Returns '(x, y, z)' for people: reports, panels and status messages.

    Args:
        v: The components.
        spec: Their format specification.
    """
    return "(" + ", ".join(number(c, spec) for c in v) + ")"


def script_vec(v: Iterable[float], spec: str = ".6g") -> str:
    """Returns '[x y z]' as EisenScript v2 blocks write vectors.

    Args:
        v: The components.
        spec: Their format specification.
    """
    return "[" + " ".join(number(c, spec) for c in v) + "]"


def rotate(v: np.ndarray, axis: np.ndarray, angle: float) -> np.ndarray:
    """Rotates a vector about an axis (Rodrigues' formula).

    Args:
        v: The vector.
        axis: The rotation axis (normalised here).
        angle: The angle in radians, counter-clockwise looking down the axis.

    Returns:
        The rotated vector.
    """
    k = np.asarray(axis, np.float64)
    k = k / (np.linalg.norm(k) or 1.0)
    c, s = math.cos(angle), math.sin(angle)
    out: np.ndarray = v * c + np.cross(k, v) * s + k * float(np.dot(k, v)) * (1.0 - c)
    return out
