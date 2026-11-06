"""Static per-rule bounds used for capacity planning (children and scene events per rule application)."""

from __future__ import annotations

import numpy as np

from ..lang.compile.program import RuleProgram
from ..lang.compile.setops import SetOp

RULE_CUSTOM, RULE_AMBIGUOUS = 0, 1


def _own(program: RuleProgram, r: int) -> tuple[int, int]:
    start, count = program.rule_act[r]
    children = events = 0
    for a in range(start, start + count):
        if program.act_kind[a] == 1:
            events += int(program.setop_code[program.act_setop[a]] == SetOp.EVENT)
            continue
        lstart, nloops = program.act_loops[a]
        product = 1
        for k in range(lstart, lstart + nloops):
            product *= max(1, int(program.loop_reps[k]))
        children += product
    return children, events


def application_limits(program: RuleProgram) -> np.ndarray:
    """int64[R, 2]: worst-case (children, events) of applying each rule (retirement/ambiguity included)."""
    n = len(program.rule_kind)
    memo: dict[int, tuple[int, int]] = {}

    def visit(r: int, stack: frozenset[int]) -> tuple[int, int]:
        if r in memo:
            return memo[r]
        if r in stack:
            return (0, 0)
        stack = stack | {r}
        kind = program.rule_kind[r]
        if kind == RULE_AMBIGUOUS:
            start, count = program.rule_alt[r]
            parts = [visit(int(program.alts[k]), stack) for k in range(start, start + count)]
            result = (max(p[0] for p in parts), max(p[1] for p in parts))
        elif kind == RULE_CUSTOM:
            result = _own(program, r)
            if program.rule_retire[r] >= 0:
                retired = visit(int(program.rule_retire[r]), stack)
                result = (max(result[0], retired[0]), max(result[1], retired[1]))
        else:
            result = (0, 0)
        memo[r] = result
        return result

    return np.asarray([visit(r, frozenset()) for r in range(n)], np.int64).reshape(n, 2)
