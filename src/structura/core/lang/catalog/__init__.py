"""Typed access to the EisenScript catalogues (the single source of truth for language vocabulary)."""

from __future__ import annotations

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


@dataclass(frozen=True, slots=True)
class PrimitiveSpec:
    name: str
    doc: str
    legacy_draws: bool = True
    emits: bool = True


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
    return OperatorSpec(str(entry["name"]), args, arity, str(entry.get("doc", "")), _aliases(entry.get("aliases")))


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
    return tuple(
        PrimitiveSpec(
            str(e["name"]), str(e.get("doc", "")), bool(e.get("legacy_draws", True)), bool(e.get("emits", True))
        )
        for e in _load("primitives.toml")["primitive"]
    )


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
        first = self.text.split("\n")[0]
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
