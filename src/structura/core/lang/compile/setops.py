"""Compile 'set' commands into builder op-codes (docs/05 §6, docs/06 §7).

Commands that influence the build (seed, limits, colour pool, syncrandom) become op-codes executed by the
kernel *when the action runs* (Structure Synth validates values lazily, so a bad value only fails if executed).
Everything else (camera, background, raytracer, template) becomes an ordered scene event.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path

from ...color import parse_color
from .pools import PoolTable, parse_pool

_INT = re.compile(r"[+-]?\d+")


class SetOp(IntEnum):
    NOP = 0
    EVENT = 1
    ERROR = 2
    MAXDEPTH = 3
    MAXOBJECTS = 4
    MINSIZE = 5
    MAXSIZE = 6
    SEED_INT = 7
    SEED_INITIAL = 8
    SYNCRANDOM = 9
    COLORPOOL = 10


@dataclass(frozen=True, slots=True)
class SceneEvent:
    key: str
    value: str


@dataclass
class SetOpTable:
    codes: list[int] = field(default_factory=list)
    ints: list[int] = field(default_factory=list)
    floats: list[float] = field(default_factory=list)
    events: list[SceneEvent] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    pools: PoolTable = field(default_factory=PoolTable)

    def add(self, code: SetOp, i: int = 0, f: float = 0.0) -> int:
        self.codes.append(int(code))
        self.ints.append(i)
        self.floats.append(f)
        return len(self.codes) - 1

    def error(self, message: str) -> int:
        self.errors.append(message)
        return self.add(SetOp.ERROR, len(self.errors) - 1)

    def event(self, key: str, value: str) -> int:
        self.events.append(SceneEvent(key, value))
        return self.add(SetOp.EVENT, len(self.events) - 1)


def _int(value: str) -> int | None:
    return int(value) if _INT.fullmatch(value.strip()) and -(2**31) <= int(value) < 2**31 else None


def _float(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


def vector_ok(value: str, count: int) -> bool:
    parts = value.replace("[", "").replace("]", "").split(" ")
    return len(parts) == count and all(_float(p) is not None for p in parts)


def _numeric(table: SetOpTable, key: str, value: str, code: SetOp, kind: str) -> int:
    number = _int(value) if kind == "integer" else _float(value)
    if number is None:
        article = "integer" if kind == "integer" else "floating-point"
        return table.error(f"Command '{key}' expected {article} parameter. Found: {value}")
    return table.add(code, int(number), float(number)) if kind == "integer" else table.add(code, 0, float(number))


def _choice(table: SetOpTable, key: str, value: str) -> int:
    lower = value.lower()
    if key == "syncrandom":
        if lower in ("true", "false"):
            return table.add(SetOp.SYNCRANDOM, int(lower == "true"))
        return table.error(f"Command 'syncrandom' expected either 'true' or 'false'. Found: {value}")
    if lower in ("old", "new"):
        return table.event("rng", lower)  # MT is always used; 'old' is reported as obsolete (W109)
    return table.error("Command 'set rng' expects either 'old' or 'new' as argument.")


def _seed(table: SetOpTable, value: str) -> int:
    if value.lower() == "initial":
        return table.add(SetOp.SEED_INITIAL)
    number = _int(value)
    if number is None:
        return table.error(f"Command 'seed' expected integer parameter or 'initial'. Found: {value}")
    return table.add(SetOp.SEED_INT, number)


_VECTOR_KEYS = {"translation": 3, "pivot": 3, "rotation": 9}
_FLOAT_EVENT_KEYS = ("scale", "perspective-angle")


def _scene(table: SetOpTable, key: str, value: str) -> int:
    if key == "background" and parse_color(value) is None:
        return table.error(f"Command 'background' expected a valid color identifier: Found: {value}")
    if key in _VECTOR_KEYS and not vector_ok(value, _VECTOR_KEYS[key]):
        kind = "matrix (such as [1 0 0 0 1 0 0 0 1])" if key == "rotation" else "vector (such as [1 3 -10.1])"
        return table.error(f"Command '{key}' expected {kind}. Found: {value}")
    if key in _FLOAT_EVENT_KEYS and _float(value) is None:
        return table.error(f"Command '{key}' expected floating point parameter. Found: {value}")
    return table.event(key, value)


def _colorpool(table: SetOpTable, value: str, script_dir: Path | None) -> int:
    pool, error = parse_pool(value, script_dir, table.pools)
    return table.error(error) if error else table.add(SetOp.COLORPOOL, pool)


_NUMERIC = {
    "maxdepth": (SetOp.MAXDEPTH, "integer"),
    "maxobjects": (SetOp.MAXOBJECTS, "integer"),
    "minsize": (SetOp.MINSIZE, "float"),
    "maxsize": (SetOp.MAXSIZE, "float"),
}
_SCENE_KEYS = ("background", "scale", "translation", "pivot", "rotation", "perspective-angle", "opengl", "template")


def compile_set(table: SetOpTable, key: str, value: str, script_dir: Path | None) -> int:
    """Return the op index for 'set key value' (unknown keys compile to a lazily raised error)."""
    if key.lower().startswith("raytracer::"):
        return table.event(key.lower(), value)
    if key in _NUMERIC:
        return _numeric(table, key, value, *_NUMERIC[key])
    handlers = {
        "syncrandom": lambda: _choice(table, key, value),
        "rng": lambda: _choice(table, key, value),
        "seed": lambda: _seed(table, value),
        "colorpool": lambda: _colorpool(table, value, script_dir),
        "recursion": lambda: table.add(SetOp.NOP),
    }
    if key in handlers:
        return handlers[key]()
    if key in _SCENE_KEYS:
        return _scene(table, key, value)
    return table.error(f"Unknown command: {key}")
