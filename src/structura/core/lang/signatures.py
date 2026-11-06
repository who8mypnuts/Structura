"""Signature help for v2 expression functions (docs/12 §3): the call enclosing the cursor and the index
of the argument being typed. Qt-free; the editor shows the result above the cursor."""

from __future__ import annotations

import re
from dataclasses import dataclass

SIGNATURES: dict[str, tuple[tuple[str, ...], str]] = {
    "sin": (("degrees",), "Sine of an angle in degrees."),
    "cos": (("degrees",), "Cosine of an angle in degrees."),
    "tan": (("degrees",), "Tangent of an angle in degrees."),
    "asin": (("x",), "Arc sine, in degrees."),
    "acos": (("x",), "Arc cosine, in degrees."),
    "atan": (("x",), "Arc tangent, in degrees."),
    "atan2": (("y", "x"), "Angle of the vector (x, y), in degrees."),
    "sqrt": (("x",), "Square root."),
    "pow": (("base", "exponent"), "base raised to exponent."),
    "exp": (("x",), "e raised to x."),
    "log": (("x",), "Natural logarithm."),
    "abs": (("x",), "Absolute value."),
    "min": (("a", "b"), "The smaller value."),
    "max": (("a", "b"), "The larger value."),
    "floor": (("x",), "Largest integer ≤ x."),
    "ceil": (("x",), "Smallest integer ≥ x."),
    "round": (("x",), "Nearest integer."),
    "clamp": (("x", "lo", "hi"), "x limited to [lo, hi]."),
    "mix": (("a", "b", "t"), "Linear interpolation a + (b − a)·t."),
}
NAME_BEFORE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*$")


@dataclass(frozen=True)
class Signature:
    name: str
    params: tuple[str, ...]
    doc: str
    active: int  # index of the argument under the cursor

    @property
    def label(self) -> str:
        return f"{self.name}({', '.join(self.params)})"


def _open_call(line: str) -> tuple[int, int] | None:
    """(index of the unmatched '(', commas after it at depth 0) scanning back from the end of ``line``."""
    depth, commas = 0, 0
    for i in range(len(line) - 1, -1, -1):
        ch = line[i]
        if ch == ")":
            depth += 1
        elif ch == "(" and depth:
            depth -= 1
        elif ch == "(":
            return i, commas
        elif ch == "," and not depth:
            commas += 1
    return None


def signature_at(text: str, pos: int) -> Signature | None:
    """The function call whose argument list contains ``pos`` (same line), or None."""
    line = text[text.rfind("\n", 0, pos) + 1 : pos]
    found = _open_call(line)
    if found is None:
        return None
    match = NAME_BEFORE.search(line[: found[0]])
    if match is None or match.group(1) not in SIGNATURES:
        return None
    params, doc = SIGNATURES[match.group(1)]
    return Signature(match.group(1), params, doc, min(found[1], len(params) - 1))
