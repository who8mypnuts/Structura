"""Save as Legacy .es (docs/14 §4.1): a copy of a script that Structure Synth 1.5 opens.

v1 scripts only lose Structura's two spellings inside transformation lists ('size' → 's', 'v' → 'brightness').
v2 scripts are flattened: '#param' becomes a 1.5 '#define' slider, '( expressions )' are evaluated at the
parameters' defaults, the v2 blocks and the 'mat' operator are dropped, and calls of the v2 primitives (cone,
torus, ellipsoid, tube) are removed. The caller writes the camera back as 'set' lines (camera_script). Each
loss is listed in the notes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .highlight import lex_line
from .legacy.preprocessor import LegacyPreprocessor
from .source import detect_dialect
from .v2.expressions import substitute_expressions
from .v2.front import front, timeline_names

ALIASES = {"size": "s", "v": "brightness"}
V2_PRIMITIVES = ("cone", "torus", "ellipsoid", "tube")
LOOPS = r"(?:(?:[\w.]+\s*\*\s*)?\{[^{}]*\}\s*)*"
V2_CALL = re.compile(LOOPS + r"\b(" + "|".join(V2_PRIMITIVES) + r")(?:::\w+)?(?:\[[^\]]*\])?(?![\w\[])")
MAT_OP = re.compile(r"\bmat\s+[A-Za-z_]\w*")
VERSION = re.compile(r"^[ \t]*#version[^\n]*\n?", re.MULTILINE)


@dataclass(frozen=True)
class LegacyCopy:
    text: str
    notes: tuple[str, ...]


def _unaliased(text: str) -> tuple[str, int]:
    """'size' and 'v' operators spelled the 1.5 way (lexer tokens only: comments are untouched)."""
    out, state, count = [], 0, 0
    for original in text.split("\n"):
        tokens, state = lex_line(original, state)
        line = original
        for start, length, role in reversed(tokens):
            word = original[start : start + length]
            if role == "operator" and word in ALIASES:
                line = line[:start] + ALIASES[word] + line[start + length :]
                count += 1
        out.append(line)
    return "\n".join(out), count


def _names(text: str, seed: int) -> dict[str, float]:
    """The defines' and sliders' default values, for evaluating expressions."""
    pre = LegacyPreprocessor(True).process(text, seed)
    names = dict(timeline_names())
    for name, value in pre.defines.items():
        try:
            names[name] = float(value.split()[0])
        except (ValueError, IndexError):
            continue
    names |= {p.name: p.default for p in pre.parameters}
    return names


def _flattened(text: str, seed: int) -> tuple[str, list[str]]:
    fr = front(text)
    notes = []
    body = substitute_expressions(fr.text, _names(fr.text, seed))
    if body != fr.text:
        notes.append("expressions were evaluated at the parameters' default values")
    decl = fr.declarations
    if decl is not None and (decl.materials or decl.lights or decl.environment or decl.render):
        notes.append("material, light, environment and render blocks were dropped (1.5 has none)")
    body, mats = MAT_OP.subn("", body)
    if mats:
        notes.append(f"{mats} 'mat' operator(s) were removed")
    body, calls = V2_CALL.subn("", body)
    if calls:
        notes.append(f"{calls} call(s) of the v2 primitives ({', '.join(V2_PRIMITIVES)}) were removed")
    lines = [line.rstrip() for line in VERSION.sub("", body, count=1).split("\n")]
    return "\n".join(lines), notes


def legacy_copy(text: str, seed: int = 0) -> LegacyCopy:
    notes: list[str] = []
    if detect_dialect(text) == 2:
        text, notes = _flattened(text, seed)
    text, aliases = _unaliased(text)
    if aliases:
        notes.append(f"{aliases} 'size' / 'v' operator(s) were spelled 's' / 'brightness'")
    return LegacyCopy(text, tuple(notes))
