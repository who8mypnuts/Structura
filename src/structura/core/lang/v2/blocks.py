"""Extract top-level v2 blocks (material, light, environment, camera, render) from the script text.

Blocks are replaced by spaces (newlines kept) so the remaining text is plain v1 with unchanged positions.
A block body is 'key value…' entries; values are numbers, [vectors], colours, names or quoted strings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Any

from ...color import rgb_of
from ...scene.declarations import LightSpec, SceneDeclarations
from ...scene.material import STATE, Material, material_from_dict, presets
from ..catalog import v2_blocks
from ..diagnostics import Diagnostic, ParseError, Severity
from ..source import Span
from .block_check import check_block, known_entries

HEADER = re.compile(r"(?m)^[ \t]*(material|light|environment|camera|render)\b[ \t]*([A-Za-z_][\w-]*)?[ \t]*\{")
VALUE = re.compile(r'"[^"]*"|\[[^\]]*\]|#[0-9A-Fa-f]+|[^\s]+')
MATERIAL_KEYS = frozenset(k.name for k in v2_blocks()["material"].keys)  # catalog/v2_blocks.toml


@dataclass
class Extracted:
    text: str
    declarations: SceneDeclarations
    diagnostics: list[Diagnostic] = field(default_factory=list)


def _value(token: str) -> Any:
    if token.startswith('"'):
        return token.strip('"')
    if token.startswith("["):
        return tuple(float(v) for v in token[1:-1].replace(",", " ").split())
    lower = token.lower()
    if lower in ("true", "false"):
        return lower == "true"
    try:
        return float(token)
    except ValueError:
        return token


def parse_body(body: str) -> dict[str, Any]:
    """'key v1 v2 …' per line ('#' and '//' comments allowed)."""
    entries: dict[str, Any] = {}
    for raw in body.splitlines():
        line = re.split(r"//|(?<!\S)#(?![0-9A-Fa-f]{3})", raw)[0].strip()
        tokens = VALUE.findall(line)
        while tokens:  # several 'key value' pairs may share a line
            key, tokens = tokens[0].lower().replace("-", "_"), tokens[1:]
            take = 2 if key == "emission" and len(tokens) > 1 else 1
            values = [_value(t) for t in tokens[:take]]
            entries[key] = values[0] if len(values) == 1 else tuple(values)
            tokens = tokens[take:]
    return entries


def _rgb(value: Any) -> tuple[float, float, float] | str:
    if value == STATE:
        return STATE
    rgb = rgb_of(value)
    if rgb is None:
        raise ValueError(f"'{value}' is not a colour")
    return rgb


def build_material(name: str, entries: dict[str, Any]) -> Material:
    """The material a block declares (unknown keys are ignored; block_check reports them)."""
    entries = {k: v for k, v in entries.items() if k in MATERIAL_KEYS}
    start = presets().get(str(entries.get("preset", "")), Material())
    data = {k: v for k, v in entries.items() if k not in ("preset", "emission", "base", "attenuation_color")}
    if "base" in entries:
        data["base"] = _rgb(entries["base"])
    if "attenuation_color" in entries:
        data["attenuation_color"] = _rgb(entries["attenuation_color"])
    if "emission" in entries:
        colour, *strength = entries["emission"] if isinstance(entries["emission"], tuple) else (entries["emission"],)
        data["emission"], data["emission_strength"] = _rgb(colour), float(strength[0]) if strength else 1.0
    return replace(material_from_dict(name, data, start), name=name)


def _closing(text: str, open_brace: int) -> int:
    depth = 0
    for i in range(open_brace, len(text)):
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            return i
    raise ParseError("Unterminated block: missing '}'", Span(open_brace, open_brace + 1), "E002")


def _blank(text: str, start: int, end: int) -> str:
    return text[:start] + "".join(c if c == "\n" else " " for c in text[start:end]) + text[end:]


def extract_blocks(text: str) -> Extracted:
    materials: dict[str, Material] = {}
    lights: list[LightSpec] = []
    singles: dict[str, dict[str, Any]] = {"environment": {}, "camera": {}, "render": {}}
    diagnostics: list[Diagnostic] = []
    out = text
    for m in reversed(list(HEADER.finditer(text))):
        end = _closing(text, m.end() - 1)
        kind, name = m.group(1), (m.group(2) or "")
        body = text[m.end() : end]
        raw = parse_body(body)
        diagnostics += check_block(kind, raw, body, m.end())
        entries = known_entries(kind, raw)
        try:
            if kind == "material":
                materials[name.lower()] = build_material(name.lower(), entries)
            elif kind == "light" and ("type" in entries or "type" not in raw):  # a bad type: E017, no light
                lights.insert(0, LightSpec(name, str(entries.pop("type", "sun")), entries))
            else:
                singles[kind] = entries
        except ValueError as exc:
            diagnostics.append(Diagnostic("E017", Severity.ERROR, f"{kind} {name}: {exc}", Span(m.start(), end + 1)))
        out = _blank(out, m.start(), end + 1)
    declarations = SceneDeclarations(materials, tuple(lights), singles["environment"], singles["camera"],
                                     singles["render"])  # fmt: skip
    return Extracted(out, declarations, diagnostics)


def enclosing_block(text: str, pos: int) -> str | None:
    """The kind of v2 block ('material', 'camera' …) whose body contains ``pos``, if any."""
    header = None
    for match in HEADER.finditer(text, 0, pos):
        header = match
    if header is None or "}" in text[header.end() : pos]:
        return None
    return header.group(1)
