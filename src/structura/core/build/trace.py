"""Ancestry of one built object: "why is this here?" (docs/06 §10.4).

The builder does not store parent links (they would cost memory on every pending state). It is deterministic,
so the ancestry is recovered by re-running the build one rule application at a time and watching where each
application's children and primitives land. The kernel is unchanged; this is a Python-side observer, and it
stops as soon as the target object has been emitted. The cost is one extra (slower) build, off the GUI thread.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..lang.compile.program import RuleProgram
from . import layout
from .driver import BuildSession


@dataclass(frozen=True)
class Step:
    rule: int  # the rule that was applied (an ambiguous rule's name covers its alternatives)
    action: int  # the call site that created the state the rule was applied to (-1 for the top level)


@dataclass
class _Observer:
    """Trace ids of the states in the kernel's buffers, in step with the kernel."""

    cur: list[int]  # ids of the current generation (BFS) or the stack (DFS)
    nxt: list[int]
    records: list[tuple[int, int, int]]  # (parent record, rule, source action)
    out: list[int]  # record of every emitted primitive


def _bfs_step(session: BuildSession, obs: _Observer, before: tuple[int, ...]) -> None:
    ctl = session.ctl
    cur_a, nextlen, nout, applied = before
    if int(ctl[layout.ST_CUR_A]) != cur_a:  # a generation ended: its children become the current list
        obs.cur, obs.nxt, nextlen = obs.nxt, [], 0
    cur_buf = session.buf_a if int(ctl[layout.ST_CUR_A]) == 1 else session.buf_b
    record = -1
    if int(ctl[layout.ST_APPLIED]) > applied:
        index = int(ctl[layout.ST_CURSOR]) - 1
        record = len(obs.records)
        src = int(cur_buf.i[index, layout.I_SRC])
        obs.records.append((obs.cur[index], int(cur_buf.i[index, layout.I_RULE]), src))
    obs.nxt.extend([record] * (int(ctl[layout.ST_NEXTLEN]) - nextlen))
    obs.out.extend([record] * (int(ctl[layout.ST_NOUT]) - nout))


def _dfs_step(session: BuildSession, obs: _Observer, before: tuple[int, ...]) -> None:
    ctl = session.ctl
    curlen, generation, nout, applied = before
    pops = int(ctl[layout.ST_GEN]) - generation  # every pop counts a 'generation' in depth-first mode
    popped = obs.cur[len(obs.cur) - pops :]
    del obs.cur[len(obs.cur) - pops :]
    record = -1
    if int(ctl[layout.ST_APPLIED]) > applied and popped:
        record = len(obs.records)
        work = session.work
        obs.records.append((popped[-1], int(work.i[0, layout.I_RULE]), int(work.i[0, layout.I_SRC])))
    children = int(ctl[layout.ST_CURLEN]) - (curlen - pops)
    obs.cur.extend([record] * children)
    obs.out.extend([record] * (int(ctl[layout.ST_NOUT]) - nout))


def ancestry(
    program: RuleProgram,
    seed: int,
    row: int,
    cancelled: Callable[[], bool] = lambda: False,
    progress: Callable[[float], None] = lambda _f: None,
) -> list[Step]:
    """The chain of rule applications that emitted SceneIR ``row``, from the top level down."""
    session = BuildSession(program, seed)
    obs = _Observer([-1], [], [], [])
    ctl, dfs = session.ctl, program.depth_first
    while len(obs.out) <= row:
        if cancelled():
            raise InterruptedError("ancestry trace cancelled")
        progress(len(obs.out) / (row + 1))
        keys = (layout.ST_CURLEN, layout.ST_GEN) if dfs else (layout.ST_CUR_A, layout.ST_NEXTLEN)
        before = (*(int(ctl[k]) for k in keys), int(ctl[layout.ST_NOUT]), int(ctl[layout.ST_APPLIED]))
        finished = session.step(1)
        (_dfs_step if dfs else _bfs_step)(session, obs, before)
        if finished and len(obs.out) <= row:
            raise ValueError(f"object {row} was not emitted (the build has {len(obs.out)})")
    steps, record = [], obs.out[row]
    while record >= 0:
        parent, rule, action = obs.records[record]
        steps.append(Step(rule, action))
        record = parent
    return steps[::-1]
