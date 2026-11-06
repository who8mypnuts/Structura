"""Typed access to the EisenScript catalogues (the single source of truth for language vocabulary)."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent


@dataclass(frozen=True, slots=True)
class Alias:
    name: str
    legacy: bool = True  # False: not accepted by Structure Synth 1.5 (info diagnostic W106)


@dataclass(frozen=True, slots=True)
class OperatorSpec:
    name: str
    args: tuple[str, ...]
    arity: tuple[int, ...]
    doc: str
    aliases: tuple[Alias, ...] = field(default_factory=tuple)
    v2: bool = False  # only in '#version 2' scripts (the v1 tokenizer never treats it as an operator)


@dataclass(frozen=True, slots=True)
class PrimitiveSpec:
    name: str
    doc: str
    legacy_draws: bool = True
    emits: bool = True
    id: int = -1  # the builder's primitive id
    v2: bool = False  # only in '#version 2' scripts
    param: float | None = None  # default of the bracket argument: 'cone[0.5]'


@dataclass(frozen=True, slots=True)
class SetSpec:
    key: str
    value: str
    doc: str
    aliases: tuple[str, ...] = ()


Entry = dict[str, Any]


def _load(name: str) -> dict[str, list[Entry]]:
    with (HERE / name).open("rb") as fh:
        return tomllib.load(fh)


def _aliases(raw: object) -> tuple[Alias, ...]:
    items = raw if isinstance(raw, list) else []
    return tuple(Alias(str(a["name"]), bool(a.get("legacy", True))) for a in items)


def _op(entry: Entry) -> OperatorSpec:
    args = tuple(str(a) for a in entry.get("args", []))
    arity = tuple(int(n) for n in entry.get("arity", [len(args)]))
    doc, aliases = str(entry.get("doc", "")), _aliases(entry.get("aliases"))
    return OperatorSpec(str(entry["name"]), args, arity, doc, aliases, bool(entry.get("v2", False)))


@cache
def operators() -> tuple[OperatorSpec, ...]:
    return tuple(_op(e) for e in _load("operators.toml")["operator"])


@cache
def modifiers() -> tuple[OperatorSpec, ...]:
    return tuple(_op(e) for e in _load("modifiers.toml")["modifier"])


@cache
def operator_names() -> dict[str, tuple[str, bool]]:
    """Every spelling (canonical or alias) → (canonical name, accepted by 1.5)."""
    table: dict[str, tuple[str, bool]] = {}
    for spec in (*operators(), *modifiers()):
        table[spec.name] = (spec.name, True)
        for alias in spec.aliases:
            table[alias.name] = (spec.name, alias.legacy)
    return table


@cache
def primitives() -> tuple[PrimitiveSpec, ...]:
    """The v1 primitives; their id is their position (the builder's legacy ids)."""
    return tuple(
        PrimitiveSpec(
            str(e["name"]), str(e.get("doc", "")), bool(e.get("legacy_draws", True)), bool(e.get("emits", True)), i
        )
        for i, e in enumerate(_load("primitives.toml")["primitive"])
    )


@cache
def v2_primitives() -> tuple[PrimitiveSpec, ...]:
    """Primitives only '#version 2' scripts have (a v2 'cylinder' replaces the v1 one, which draws nothing)."""
    return tuple(_v2_primitive(e) for e in _load("primitives.toml")["v2_primitive"])


@cache
def all_primitives() -> tuple[PrimitiveSpec, ...]:
    """Every primitive name once (for highlighting, completion, hover and the reference)."""
    v1 = primitives()
    names = {p.name for p in v1}
    return (*v1, *(p for p in v2_primitives() if p.name not in names))


def _v2_primitive(e: Entry) -> PrimitiveSpec:
    param = float(e["param"]) if "param" in e else None
    return PrimitiveSpec(str(e["name"]), str(e.get("doc", "")), id=int(e["id"]), v2=True, param=param)


@cache
def set_commands() -> tuple[SetSpec, ...]:
    return tuple(
        SetSpec(str(e["key"]), str(e["value"]), str(e.get("doc", "")), tuple(str(a) for a in e.get("aliases", [])))
        for e in _load("set_commands.toml")["set"]
    )


@dataclass(frozen=True, slots=True)
class Snippet:
    group: str
    text: str

    @property
    def title(self) -> str:
        first = re.sub(r"\$\{\d+:([^}]*)\}|\$\d+", r"\1", self.text).split("\n")[0]  # tab stops shown plainly
        return first if len(first) <= 60 else first[:57] + "…"


@cache
def snippets() -> tuple[Snippet, ...]:
    return tuple(Snippet(str(g["group"]), str(item)) for g in _load("snippets.toml")["snippet"] for item in g["items"])


@dataclass(frozen=True, slots=True)
class RaytracerKey:
    name: str
    value: str
    doc: str


@cache
def raytracer_keys() -> tuple[RaytracerKey, ...]:
    return tuple(RaytracerKey(str(k["name"]), str(k["value"]), str(k["doc"])) for k in _load("raytracer.toml")["key"])


@dataclass(frozen=True, slots=True)
class DiagnosticSpec:
    code: str
    severity: str  # "error" | "warning" | "info"
    title: str
    doc: str
    fix: str = ""  # the quick fix offered (core.lang.fixes), if any


@cache
def diagnostic_specs() -> dict[str, DiagnosticSpec]:
    entries = _load("diagnostics.toml")["diagnostic"]
    return {
        str(e["code"]): DiagnosticSpec(str(e["code"]), str(e["severity"]), str(e["title"]), str(e["doc"]),
                                       str(e.get("fix", "")))
        for e in entries
    }  # fmt: skip


@dataclass(frozen=True, slots=True)
class BlockKey:
    name: str
    value: str
    doc: str


@dataclass(frozen=True, slots=True)
class BlockSpec:
    name: str
    doc: str
    keys: tuple[BlockKey, ...]


@cache
def v2_blocks() -> dict[str, BlockSpec]:
    return {
        str(b["name"]): BlockSpec(str(b["name"]), str(b["doc"]),
                                  tuple(BlockKey(str(k["name"]), str(k["value"]), str(k["doc"])) for k in b["key"]))
        for b in _load("v2_blocks.toml")["block"]
    }  # fmt: skip
