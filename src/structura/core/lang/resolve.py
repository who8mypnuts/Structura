"""Build the rule set and resolve rule references (docs/05 §4.5, docs/06 §6).

Order of the rule list: the built-in primitives, the implicit TopLevelRule, then user rules in source order.
Several definitions with the same name merge into an ambiguous (weighted) rule. References resolve to rules,
primitives, tagged primitive copies ('box::shiny') or inline triangles ('triangle[x,y,z;x,y,z;x,y,z]').
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import IntEnum

from ..errors import BuildError, UnresolvedRuleError
from .ast import Action, CallAction, Program, RuleDef
from .catalog import primitives

TOP_LEVEL = "TopLevelRule"
_TRIANGLE = re.compile(r"triangle\[(.*)\]")


class RuleKind(IntEnum):
    CUSTOM = 0
    AMBIGUOUS = 1
    PRIMITIVE = 2
    TRIANGLE = 3


PRIMITIVE_NAMES = tuple(spec.name for spec in primitives())  # order defines primitive kind ids


@dataclass
class ResolvedRule:
    kind: RuleKind
    name: str
    actions: tuple[Action, ...] = ()
    weight: float = 1.0
    maxdepth: int = -1
    retirement: str | None = None
    alternatives: list[int] = field(default_factory=list)  # AMBIGUOUS: indices of CUSTOM rules
    primitive: int = -1  # index into PRIMITIVE_NAMES
    tag: str = ""
    triangle: tuple[tuple[float, float, float], ...] = ()


@dataclass
class RuleSet:
    rules: list[ResolvedRule]
    by_name: dict[str, int]
    top: int
    depth_first: bool
    tags: list[str]

    def index(self, name: str) -> int:
        return self.by_name[name]


def _custom(rule: RuleDef) -> ResolvedRule:
    depth = -1 if rule.maxdepth is None else rule.maxdepth
    return ResolvedRule(RuleKind.CUSTOM, rule.name, rule.body, rule.weight, depth, rule.retirement)


def _add_rule(rs: RuleSet, rule: RuleDef) -> None:
    new = _custom(rule)
    existing = rs.by_name.get(rule.name)
    if existing is None:
        rs.rules.append(new)
        rs.by_name[rule.name] = len(rs.rules) - 1
        return
    old = rs.rules[existing]
    if old.kind is RuleKind.PRIMITIVE:
        raise BuildError(
            f"A primitive rule already exists with the name: '{rule.name}'. New definitions can not merged."
        )
    rs.rules.append(new)
    if old.kind is RuleKind.AMBIGUOUS:
        old.alternatives.append(len(rs.rules) - 1)
        return
    rs.rules.append(ResolvedRule(RuleKind.AMBIGUOUS, rule.name, alternatives=[existing, len(rs.rules) - 1]))
    rs.by_name[rule.name] = len(rs.rules) - 1


def build_rule_set(program: Program) -> RuleSet:
    rules = [ResolvedRule(RuleKind.PRIMITIVE, name, primitive=i) for i, name in enumerate(PRIMITIVE_NAMES)]
    rules.append(ResolvedRule(RuleKind.CUSTOM, TOP_LEVEL, program.top))
    rs = RuleSet(rules, {r.name: i for i, r in enumerate(rules)}, len(rules) - 1, program.depth_first, [""])
    for rule in program.rules:
        _add_rule(rs, rule)
    _resolve_references(rs)
    return rs


def _references(rule: ResolvedRule) -> list[str]:
    refs = [a.target for a in rule.actions if isinstance(a, CallAction)]
    return refs + ([rule.retirement] if rule.retirement else [])


def _resolve_references(rs: RuleSet) -> None:
    for rule in list(rs.rules):
        for name in _references(rule):
            if name not in rs.by_name:
                rs.rules.append(_resolve_missing(rs, name))
                rs.by_name[name] = len(rs.rules) - 1


def _resolve_missing(rs: RuleSet, name: str) -> ResolvedRule:
    parts = name.split("::")
    if len(parts) == 2:
        base, tag = parts
        if base not in rs.by_name:
            raise UnresolvedRuleError(f"Unable to resolve base rule name: {base} for rule {name}", base)
        base_rule = rs.rules[rs.by_name[base]]
        if base_rule.kind is not RuleKind.PRIMITIVE:
            raise BuildError(f"Only primitive rules (box, sphere, ...) may have a class specifier: {name} is invalid")
        if tag not in rs.tags:
            rs.tags.append(tag)
        return ResolvedRule(RuleKind.PRIMITIVE, name, primitive=base_rule.primitive, tag=tag)
    match = _TRIANGLE.fullmatch(name)
    if match:
        return ResolvedRule(RuleKind.TRIANGLE, name, triangle=_triangle_points(match.group(1), name))
    raise UnresolvedRuleError(f"Unable to resolve rule: {name}", name)


def _triangle_points(spec: str, name: str) -> tuple[tuple[float, float, float], ...]:
    corners = spec.split(";")
    if len(corners) != 3:
        raise BuildError("Unable to parse Triangle definition - must be triangle(p1;p2;p3) - found : " + name)
    points = []
    for corner in corners:
        coords = corner.split(",")
        if len(coords) != 3:
            raise BuildError(
                f"Unable to parse Triangle definition - coordinates must be like '0.1,0.2,0.3' - found : {corner}"
            )
        try:
            x, y, z = (float(c) for c in coords)
        except ValueError as exc:
            raise BuildError(f"Unable to parse Triangle definition - error in coordinate - found in : {name}") from exc
        points.append((x, y, z))
    return tuple(points)
