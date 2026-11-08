"""A static object estimate (docs/06 §6 'Static size estimate', docs/12 §2.2 inlay hints): each rule's expected
children per application (ambiguous alternatives weighted, loop counts multiplied) make a branching process;
iterating it per generation from a top-level call gives the expected number of primitives, bounded by the
script's 'set maxdepth' and 'set maxobjects' (1.5's defaults otherwise) exactly as the builder applies them.
A rule's own maxdepth stops it after that many generations (exact for self-recursion, rougher through other
rules). Deterministic scripts get the builder's count; with ambiguous rules it is the expectation, and
retirement and size limits are ignored."""

from __future__ import annotations

import numpy as np

from .ast import CallAction, Program, SetAction
from .catalog import all_primitives

DEFAULT_DEPTH, DEFAULT_OBJECTS = 1000, 100_000  # core.build.driver's defaults (1.5's)


def _target(name: str) -> str:
    return name.split("::", maxsplit=1)[0].split("[", maxsplit=1)[0].lower()


def _multiplicity(call: CallAction) -> float:
    product = 1.0
    for loop in call.loops:
        product *= max(1, loop.count)
    return product


def _limits(program: Program) -> tuple[int, int]:
    depth, objects = DEFAULT_DEPTH, DEFAULT_OBJECTS
    for action in program.top:
        if isinstance(action, SetAction) and action.value.isdigit():
            depth = int(action.value) if action.key == "maxdepth" else depth
            objects = int(action.value) if action.key == "maxobjects" else objects
    return depth, objects


class Estimator:
    def __init__(self, program: Program) -> None:
        self.names = sorted({r.name.lower() for r in program.rules})
        self.index = {n: i for i, n in enumerate(self.names)}
        self.primitives = {p.name for p in all_primitives()}
        n = len(self.names)
        self.children, self.objects = np.zeros((n, n)), np.zeros(n)
        totals: dict[str, float] = {}
        for rule in program.rules:
            totals[rule.name.lower()] = totals.get(rule.name.lower(), 0.0) + rule.weight
        for rule in program.rules:
            share = rule.weight / (totals[rule.name.lower()] or 1.0)
            for call in (a for a in rule.body if isinstance(a, CallAction)):
                self._add(self.index[rule.name.lower()], call, share)
        self.depth, self.cap = _limits(program)
        self.maxdepth = np.full(n, np.inf)  # a rule's own limit: the fewest generations any alternative allows
        for rule in program.rules:
            if rule.maxdepth is not None:
                i = self.index[rule.name.lower()]
                self.maxdepth[i] = min(self.maxdepth[i], rule.maxdepth)

    def _add(self, row: int, call: CallAction, share: float) -> None:
        target, count = _target(call.target), share * _multiplicity(call)
        if target in self.index:
            self.children[row, self.index[target]] += count
        elif target in self.primitives:
            self.objects[row] += count

    def call(self, call: CallAction) -> tuple[float, bool]:
        """(expected objects of one top-level call, whether the object limit cuts it). Like the builder, a
        generation only starts while fewer states are pending, and fewer actions were executed, than the
        limit — the executed-actions counter includes rule calls, as in 1.5 — and the top level and the last
        generation use up two of the maxdepth generations."""
        target, count = _target(call.target), _multiplicity(call)
        if target not in self.index:
            return (count, False) if target in self.primitives else (0.0, False)
        population = np.zeros(len(self.names))
        population[self.index[target]] = count
        actions = self.objects + self.children.sum(axis=1)  # per application: primitives and rule calls
        total, executed = 0.0, count
        for generation in range(max(0, self.depth - 2)):
            population[self.maxdepth <= generation] = 0.0
            if population.sum() < 1e-9:
                break
            if executed >= self.cap or population.sum() >= self.cap:
                return total, True
            total += float(population @ self.objects)
            executed += float(population @ actions)
            population = population @ self.children
        return total, False


def estimate_label(objects: float, capped: bool) -> str:
    if capped:
        return f"≈ {_short(objects)} objects (limit)"
    return f"≈ {_short(objects)} object{'s' if round(objects) != 1 else ''}"


def _short(value: float) -> str:
    for limit, suffix in ((1e9, "G"), (1e6, "M"), (1e3, "k")):
        if value >= limit:
            return f"{value / limit:.3g}{suffix}"
    return f"{value:.0f}"
