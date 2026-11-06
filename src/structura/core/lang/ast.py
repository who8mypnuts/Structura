"""EisenScript abstract syntax tree (shared by the v1 and v2 front ends)."""

from __future__ import annotations

from dataclasses import dataclass

from .source import Span


@dataclass(frozen=True, slots=True)
class TransformOp:
    """One operator inside '{ … }'. ``name`` is canonical (aliases resolved); args are floats or strings."""

    name: str
    args: tuple[float | str, ...]
    span: Span


@dataclass(frozen=True, slots=True)
class Loop:
    """'count * { ops }'. A bare '{ ops }' list is a loop with count 1."""

    count: int
    ops: tuple[TransformOp, ...]
    span: Span


@dataclass(frozen=True, slots=True)
class CallAction:
    """Optional loops followed by a rule reference (a rule, primitive, 'prim::tag', 'triangle[…]')."""

    loops: tuple[Loop, ...]
    target: str
    span: Span


@dataclass(frozen=True, slots=True)
class SetAction:
    key: str
    value: str
    span: Span


Action = CallAction | SetAction


@dataclass(frozen=True, slots=True)
class RuleDef:
    name: str
    body: tuple[Action, ...]
    span: Span
    weight: float = 1.0
    maxdepth: int | None = None
    retirement: str | None = None


@dataclass(frozen=True, slots=True)
class Program:
    """A parsed script: top-level actions (the implicit TopLevelRule) and rule definitions in source order."""

    top: tuple[Action, ...]
    rules: tuple[RuleDef, ...]
    depth_first: bool = False
