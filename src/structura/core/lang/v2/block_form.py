"""v2 blocks as forms (PLAN Q2: the Lights panel's property editor): the catalogue's keys become ParamSpecs,
a block's parsed entries become form values and back, and a block is written out as text. Qt-free; the panel
shows the specs with the generic ParamForm.

Numbers and ranges are spin boxes, word choices are lists; vectors and colours are edited as the text a
script would hold ('[0 4 2]', '#ffcc80'). Keys whose documentation starts with the light types they apply to
('spot, rect: …') are only offered for those types."""

from __future__ import annotations

import re
from typing import Any

from ...params import ParamSpec, ParamType
from ...scene.vectors import number, script_vec
from ..catalog import v2_blocks
from .block_check import RANGE, verdict
from .blocks import parse_body

WORD_CHOICES = re.compile(r"^[a-z_-]+( \| [a-z_-]+)+$")
APPLIES = re.compile(r"^([a-z]+(?:, [a-z]+)*): ")


def applies(doc: str, kind_type: str) -> bool:
    """Whether a key documented as ``doc`` belongs to a block of type ``kind_type`` ('spot, rect: …')."""
    match = APPLIES.match(doc)
    return match is None or kind_type in match.group(1).split(", ")


def _spec(key: str, grammar: str, doc: str) -> ParamSpec:
    title = key.replace("_", " ").capitalize()
    if WORD_CHOICES.match(grammar):
        choices = tuple(c.strip() for c in grammar.split("|"))
        return ParamSpec(key, ParamType.ENUM, choices[0], title, doc, choices)
    bounds = RANGE.match(grammar)
    if bounds is not None:
        return ParamSpec(key, ParamType.FLOAT, 0.0, title, doc, range=(float(bounds.group(1)), float(bounds.group(2))))
    if grammar in ("number", "float", "degrees", "int"):
        kind = ParamType.INT if grammar == "int" else ParamType.FLOAT
        return ParamSpec(key, kind, 0, title, doc, range=(-1e9, 1e9))
    return ParamSpec(key, ParamType.STRING, "", title, f"{doc} ({grammar})")


def block_specs(kind: str, kind_type: str = "") -> tuple[ParamSpec, ...]:
    """Form fields of a block kind (for lights: those that apply to ``kind_type``), in catalogue order."""
    keys = v2_blocks()[kind].keys
    return tuple(_spec(k.name, k.value, k.doc) for k in keys if not kind_type or applies(k.doc, kind_type))


def value_text(value: Any) -> str:
    """A parsed block value as the script writes it."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, tuple):
        return script_vec(value, ".4g")
    if isinstance(value, float):
        return number(value, ".6g")
    return str(value)


def form_values(specs: tuple[ParamSpec, ...], entries: dict[str, Any]) -> dict[str, Any]:
    """The entries a block sets, as values of its form (vectors and colours as text)."""
    out: dict[str, Any] = {}
    for spec in specs:
        if spec.key in entries:
            value = entries[spec.key]
            out[spec.key] = value_text(value) if spec.type in (ParamType.STRING, ParamType.ENUM) else value
    return out


def entries_of(specs: tuple[ParamSpec, ...], values: dict[str, Any], grammar: dict[str, str]) -> dict[str, Any]:
    """Form values → block entries (text fields parsed as a script line; values that do not fit are dropped)."""
    out: dict[str, Any] = {}
    for spec in specs:
        if spec.key not in values or values[spec.key] in ("", None):
            continue
        value = values[spec.key]
        if spec.type == ParamType.STRING and isinstance(value, str):  # text as a script would hold it
            value = parse_body(f"{spec.key} {value}").get(spec.key, value)
        if verdict(grammar[spec.key], value).ok:
            out[spec.key] = value
    return out


def block_text(kind: str, name: str, entries: dict[str, Any]) -> str:
    """'kind name {' + one 'key value' line per entry + '}'."""
    head = f"{kind} {name} {{" if name else f"{kind} {{"
    return "\n".join([head, *(f"  {key} {value_text(value)}" for key, value in entries.items()), "}"])
