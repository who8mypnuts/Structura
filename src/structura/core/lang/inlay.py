"""Inlay hints (docs/12 §2.2), Qt-free: the probability of each alternative of an ambiguous rule, the number
of children a chain of loops produces, and the material a tag resolves to (v2). Positions are original-text
offsets; the editor shows each line's hints after its text."""

from __future__ import annotations

from dataclasses import dataclass

from ..scene.declarations import SceneDeclarations
from ..scene.material import presets
from .ast import CallAction, Program
from .position_map import PositionMap


@dataclass(frozen=True)
class Hint:
    position: int  # where it belongs in the original text (the editor draws it at the end of that line)
    text: str
    kind: str  # "probability" | "loops" | "material"


def probability_hints(program: Program, pm: PositionMap) -> list[Hint]:
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}
    for rule in program.rules:
        totals[rule.name] = totals.get(rule.name, 0.0) + rule.weight
        counts[rule.name] = counts.get(rule.name, 0) + 1
    return [Hint((pm.span(r.span) or r.span).start, f"⟶ {100 * r.weight / (totals[r.name] or 1):.1f}%", "probability")
            for r in program.rules if counts[r.name] > 1]  # fmt: skip


def _calls(program: Program) -> list[CallAction]:
    bodies = [program.top, *(r.body for r in program.rules)]
    return [a for body in bodies for a in body if isinstance(a, CallAction)]


def loop_hints(program: Program, pm: PositionMap) -> list[Hint]:
    hints = []
    for call in _calls(program):
        counts = [loop.count for loop in call.loops if loop.count > 1]
        if counts:
            product = 1
            for n in counts:
                product *= n
            label = f"×{product}" if len(counts) == 1 else f"×{product} ({' × '.join(map(str, counts))})"
            hints.append(Hint((pm.span(call.span) or call.span).end, label, "loops"))
    return hints


def material_hints(program: Program, pm: PositionMap, declarations: SceneDeclarations | None) -> list[Hint]:
    if declarations is None:
        return []
    builtin, hints, seen = presets(), [], set()
    for call in _calls(program):
        tag = call.target.partition("::")[2]
        if not tag or (tag, call.span) in seen:
            continue
        seen.add((tag, call.span))
        where = (pm.span(call.span) or call.span).end
        if tag in declarations.materials:
            hints.append(Hint(where, f"◆ {tag}", "material"))
        elif tag in builtin:
            hints.append(Hint(where, f"◆ {tag} (preset)", "material"))
    return hints


def inlay_hints(program: Program, pm: PositionMap, declarations: SceneDeclarations | None) -> tuple[Hint, ...]:
    found = [*probability_hints(program, pm), *loop_hints(program, pm), *material_hints(program, pm, declarations)]
    return tuple(sorted(found, key=lambda h: h.position))
