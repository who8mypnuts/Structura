"""Extract top-level v2 blocks (material, light, environment, camera, render) from the script text.

Blocks are replaced by spaces (newlines kept) so the remaining text is plain v1 with unchanged positions.
A block body is 'key value…' entries; values are numbers, [vectors], colours, names or quoted strings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Any

from ...color import parse_color
from ...scene.declarations import LightSpec, SceneDeclarations
from ...scene.material import STATE, Material, material_from_dict, presets
from ..diagnostics import Diagnostic, ParseError, Severity
from ..source import Span

HEADER = re.compile(r"(?m)^[ \t]*(material|light|environment|camera|render)\b[ \t]*([A-Za-z_][\w-]*)?[ \t]*\{")
VALUE = re.compile(r'"[^"]*"|\[[^\]]*\]|#[0-9A-Fa-f]+|[^\s]+')
MATERIAL_KEYS = {"base", "metallic", "roughness", "specular", "ior", "transmission", "emission", "opacity",
                 "coat", "coat_roughness", "anisotropy", "attenuation_color", "attenuation_distance",
                 "thin_walled", "transmission_roughness", "preset", "model"}  # fmt: skip


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
    if isinstance(value, tuple) and len(value) == 3:
        return (float(value[0]), float(value[1]), float(value[2]))
    c = parse_color(str(value))
    if c is None:
        raise ValueError(f"'{value}' is not a colour")
    return (c.r / 65535, c.g / 65535, c.b / 65535)


def build_material(name: str, entries: dict[str, Any]) -> Material:
    unknown = set(entries) - MATERIAL_KEYS
    if unknown:
        raise ValueError(f"unknown material keys: {', '.join(sorted(unknown))}")
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
        entries = parse_body(text[m.end() : end])
        try:
            if kind == "material":
                materials[name.lower()] = build_material(name.lower(), entries)
            elif kind == "light":
                lights.insert(0, LightSpec(name, str(entries.pop("type", "sun")), entries))
            else:
                singles[kind] = entries
        except ValueError as exc:
            diagnostics.append(Diagnostic("E017", Severity.ERROR, f"{kind} {name}: {exc}", Span(m.start(), end + 1)))
        out = _blank(out, m.start(), end + 1)
    declarations = SceneDeclarations(materials, tuple(lights), singles["environment"], singles["camera"],
                                     singles["render"])  # fmt: skip
    return Extracted(out, declarations, diagnostics)
