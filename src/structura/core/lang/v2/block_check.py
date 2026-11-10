"""Check the keys and values of v2 blocks against catalog/v2_blocks.toml (PLAN Q2): the catalogue that drives
completion, hover and the language reference also says what each key accepts.

A key the block does not have is W115 (ignored); a value of the wrong kind — or a choice that does not exist,
like an unknown light type or material preset — is E017; a number outside the documented range is W117 (the
renderer clamps or uses it as given). The 'value' column's grammar: alternatives separated by '|', each one of
number / float / degrees / int / colour / color / bool / name / "path.ext" / [x y z] / [w h] / WxH / A..B, or a
literal word."""

from __future__ import annotations

import difflib
import re
from collections.abc import Iterator
from dataclasses import dataclass
from functools import cache
from typing import Any

from ...color import rgb_of
from ...scene.material import presets
from ..catalog import v2_blocks
from ..diagnostics import Diagnostic, diagnostic
from ..source import Span

RANGE = re.compile(r"^(-?[\d.]+)\.\.(-?[\d.]+)$")
SIZE = re.compile(r"^\d+x\d+$", re.I)
SENSOR = re.compile(r"^\d+(\.\d+)?x\d+(\.\d+)?$", re.I)
FREE = ("colour strength",)  # validated where the value is used (material emission)


@dataclass(frozen=True)
class Verdict:
    ok: bool  # the value has an accepted form
    in_range: bool = True
    expected: str = ""


@cache
def known_keys(kind: str) -> dict[str, str]:
    """Key → value grammar of a block kind."""
    return {k.name: k.value for k in v2_blocks()[kind].keys}


def _number(value: Any) -> bool:
    return isinstance(value, float) and not isinstance(value, bool)


def _form_ok(form: str, value: Any) -> bool:  # noqa: PLR0911 - one branch per form of the grammar
    if isinstance(value, str) and value.lower() == form:  # a literal word ('color' is also an environment type)
        return True
    if form in ("number", "float", "degrees"):
        return _number(value)
    if form == "int":
        return _number(value) and float(value).is_integer()
    if form in ("colour", "color"):
        return not _number(value) and rgb_of(value) is not None
    if form == "bool":
        return isinstance(value, bool)
    if form == "name" or form.startswith('"path.'):  # "path.exr", "path.cube": a file name
        return isinstance(value, str)
    if form == "[x y z]":
        return isinstance(value, tuple) and len(value) == 3
    if form == "[w h]":
        return (isinstance(value, tuple) and len(value) == 2) or _number(value)
    if form == "[x y]":
        return isinstance(value, tuple) and len(value) == 2
    if form == "WxH":
        return isinstance(value, str) and bool(SIZE.match(value))
    if form == "WxH mm":
        return isinstance(value, str) and bool(SENSOR.match(value))
    return isinstance(value, bool) and str(value).lower() == form  # 'true | false' reads as a bool


def verdict(grammar: str, value: Any) -> Verdict:
    """Whether ``value`` (as parse_body read it) fits ``grammar`` (a catalogue 'value')."""
    if grammar in FREE:
        return Verdict(True)
    in_range = False
    for form in (f.strip() for f in grammar.split("|")):
        bounds = RANGE.match(form)
        if bounds is not None:
            if _number(value):
                low, high = float(bounds.group(1)), float(bounds.group(2))
                if low <= float(value) <= high:
                    return Verdict(True)
                in_range = True  # a number, but outside
        elif _form_ok(form, value):
            return Verdict(True)
    return Verdict(in_range, in_range=False, expected=grammar) if in_range else Verdict(False, expected=grammar)


def _key_span(body: str, offset: int, key: str) -> Span:
    pattern = re.compile(r"(?<![\w-])" + key.replace("_", "[-_]") + r"(?![\w-])", re.I)
    match = pattern.search(body)
    return Span(offset + match.start(), offset + match.end()) if match else Span(offset, offset)


def _show(value: Any) -> str:
    if isinstance(value, tuple):
        return "[" + " ".join(f"{v:g}" if _number(v) else str(v) for v in value) + "]"
    return f"{value:g}" if _number(value) else str(value)


def _problems(kind: str, entries: dict[str, Any]) -> Iterator[tuple[str, str, str]]:
    """(key, message, diagnostic code) of every problem."""
    keys = known_keys(kind)
    for key, value in entries.items():
        if key not in keys:
            close = difflib.get_close_matches(key, keys, n=1)
            hint = f" (did you mean '{close[0]}'?)" if close else ""
            yield key, f"'{key}' is not a key of {kind} blocks{hint}", "W115"
            continue
        result = verdict(keys[key], value)
        if not result.ok:
            yield key, f"{kind} {key}: expected {result.expected}, got '{_show(value)}'", "E017"
        elif not result.in_range:
            yield key, f"{kind} {key}: {_show(value)} is outside {result.expected}", "W117"
    preset = entries.get("preset")
    if kind == "material" and preset is not None and str(preset) not in presets():
        yield "preset", f"unknown material preset '{preset}' (one of: {', '.join(sorted(presets()))})", "E017"


def check_block(kind: str, entries: dict[str, Any], body: str, offset: int) -> list[Diagnostic]:
    """Diagnostics for one block's parsed ``entries``; ``body`` is its text, starting at ``offset``."""
    return [diagnostic(code, message, _key_span(body, offset, key)) for key, message, code in _problems(kind, entries)]


def known_entries(kind: str, entries: dict[str, Any]) -> dict[str, Any]:
    """``entries`` without what check_block reports as unknown (W115) or malformed (E017): those are ignored,
    so a typo never reaches the renderer. Out-of-range numbers (W117) are kept."""
    keys = known_keys(kind)
    kept = {k: v for k, v in entries.items() if k in keys and verdict(keys[k], v).ok}
    if kind == "material" and str(kept.get("preset", "")) not in presets():
        kept.pop("preset", None)
    return kept
