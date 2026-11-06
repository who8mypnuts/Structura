"""Build the rule set and resolve rule references (docs/05 §4.5, docs/06 §6).

Order of the rule list: the built-in primitives, the implicit TopLevelRule, then user rules in source order.
Several definitions with the same name merge into an ambiguous (weighted) rule. References resolve to rules,
primitives, tagged primitive copies ('box::shiny') or inline triangles ('triangle[x,y,z;x,y,z;x,y,z]').
v2 scripts also have the v2 primitives, some with a bracket argument ('cone[0.5]', 'torus[0.1]::gold').
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from enum import IntEnum

from ..errors import BuildError, UnresolvedRuleError
from .ast import Action, CallAction, Program, RuleDef
from .catalog import primitives, v2_primitives

TOP_LEVEL = "TopLevelRule"
_TRIANGLE = re.compile(r"triangle\[(.*)\]")
_BRACKET = re.compile(r"(\w+)\[(.*)\]")


class RuleKind(IntEnum):
    CUSTOM = 0
    AMBIGUOUS = 1
    PRIMITIVE = 2
    TRIANGLE = 3


PRIMITIVE_NAMES = tuple(spec.name for spec in primitives())  # v1; order defines the primitive ids


@dataclass
class ResolvedRule:
    kind: RuleKind
    name: str
    actions: tuple[Action, ...] = ()
    weight: float = 1.0
    maxdepth: int = -1
    retirement: str | None = None
    alternatives: list[int] = field(default_factory=list)  # AMBIGUOUS: indices of CUSTOM rules
    primitive: int = -1  # primitive id (catalog)
    tag: str = ""
    triangle: tuple[tuple[float, float, float], ...] = ()
    param: float = 0.0  # bracket argument of cone[r] / torus[r] / tube[r]


@dataclass
class RuleSet:
    rules: list[ResolvedRule]
    by_name: dict[str, int]
    top: int
    depth_first: bool
    tags: list[str]
    v2: bool = False

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
            f"A primitive rule already exists with the name: '{rule.name}'. New definitions can not merged.",
            code="E010",
        )
    rs.rules.append(new)
    if old.kind is RuleKind.AMBIGUOUS:
        old.alternatives.append(len(rs.rules) - 1)
        return
    rs.rules.append(ResolvedRule(RuleKind.AMBIGUOUS, rule.name, alternatives=[existing, len(rs.rules) - 1]))
    rs.by_name[rule.name] = len(rs.rules) - 1


def _primitive_rules(v2: bool) -> list[ResolvedRule]:
    rules = {p.name: ResolvedRule(RuleKind.PRIMITIVE, p.name, primitive=p.id) for p in primitives()}
    for p in v2_primitives() if v2 else ():
        rules[p.name] = ResolvedRule(RuleKind.PRIMITIVE, p.name, primitive=p.id, param=p.param or 0.0)
    return list(rules.values())


def build_rule_set(program: Program, v2: bool = False) -> RuleSet:
    rules = _primitive_rules(v2)
    rules.append(ResolvedRule(RuleKind.CUSTOM, TOP_LEVEL, program.top))
    by_name = {r.name: i for i, r in enumerate(rules)}
    rs = RuleSet(rules, by_name, len(rules) - 1, program.depth_first, [""], v2)
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
        return _tagged(rs, name, *parts)
    match = _TRIANGLE.fullmatch(name)
    if match:
        return ResolvedRule(RuleKind.TRIANGLE, name, triangle=_triangle_points(match.group(1), name))
    bracketed = _bracket_primitive(rs, name)
    if bracketed is not None:
        return bracketed
    raise UnresolvedRuleError(f"Unable to resolve rule: {name}", name)


def _tagged(rs: RuleSet, name: str, base: str, tag: str) -> ResolvedRule:
    """'box::shiny', 'cone[0.5]::gold', 'triangle[…]::glass': a copy of a primitive with a tag."""
    if base not in rs.by_name and "[" in base:
        rs.rules.append(_resolve_missing(rs, base))
        rs.by_name[base] = len(rs.rules) - 1
    if base not in rs.by_name:
        raise UnresolvedRuleError(f"Unable to resolve base rule name: {base} for rule {name}", base)
    base_rule = rs.rules[rs.by_name[base]]
    if base_rule.kind not in (RuleKind.PRIMITIVE, RuleKind.TRIANGLE):
        raise BuildError(
            f"Only primitive rules (box, sphere, ...) may have a class specifier: {name} is invalid", code="E013"
        )
    if tag not in rs.tags:
        rs.tags.append(tag)
    return replace(base_rule, name=name, tag=tag, alternatives=[])


def _bracket_primitive(rs: RuleSet, name: str) -> ResolvedRule | None:
    """'cone[0.5]' → the cone primitive with parameter 0.5 (v2 primitives that take an argument)."""
    match = _BRACKET.fullmatch(name)
    spec = next((p for p in v2_primitives() if match and p.name == match.group(1)), None) if rs.v2 else None
    if match is None or spec is None or spec.param is None:
        return None
    try:
        value = float(match.group(2))
    except ValueError as exc:
        raise BuildError(f"'{name}': the argument of {spec.name}[…] must be a number", code="E014") from exc
    return ResolvedRule(RuleKind.PRIMITIVE, name, primitive=spec.id, param=value)


def _triangle_points(spec: str, name: str) -> tuple[tuple[float, float, float], ...]:
    corners = spec.split(";")
    if len(corners) != 3:
        raise BuildError(
            "Unable to parse Triangle definition - must be triangle(p1;p2;p3) - found : " + name, code="E014"
        )
    points = []
    for corner in corners:
        coords = corner.split(",")
        if len(coords) != 3:
            raise BuildError(
                f"Unable to parse Triangle definition - coordinates must be like '0.1,0.2,0.3' - found : {corner}",
                code="E014",
            )
        try:
            x, y, z = (float(c) for c in coords)
        except ValueError as exc:
            message = f"Unable to parse Triangle definition - error in coordinate - found in : {name}"
            raise BuildError(message, code="E014") from exc
        points.append((x, y, z))
    return tuple(points)
