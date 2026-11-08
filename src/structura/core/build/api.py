"""Public builder API (docs/06 §1)."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import numpy as np

from ..lang.compile.program import RuleProgram
from ..scene.ir import LEGACY_KIND, SceneIR
from .driver import BuildSession, BuildStats

SLICE_BUDGET = 20_000  # rule applications per kernel call


@dataclass(frozen=True)
class BuildResult:
    scene: SceneIR
    stats: BuildStats


def scene_of(session: BuildSession) -> SceneIR:
    """The SceneIR of a (finished or partial) build session."""
    outbuf, program = session.outbuf, session.program
    n = session.emitted
    vectors = outbuf.xf[:n].reshape(n, 4, 3)  # base, d1, d2, d3
    xform = np.empty((n, 3, 4), np.float32)
    xform[:, :, 0], xform[:, :, 1], xform[:, :, 2], xform[:, :, 3] = (
        vectors[:, 1],
        vectors[:, 2],
        vectors[:, 3],
        vectors[:, 0],
    )
    n_aux, n_ev = int(session.ctl[13]), int(session.ctl[14])
    events = tuple((program.events[int(e)], int(g), int(k)) for e, g, k in outbuf.events[:n_ev])
    return SceneIR(
        LEGACY_KIND[outbuf.kind[:n]],
        xform,
        outbuf.rgba[:n].copy(),
        outbuf.tag[:n].copy(),
        outbuf.src[:n].copy(),
        outbuf.gen[:n].copy(),
        outbuf.aux[:n].copy(),
        outbuf.aux_f[:n_aux].copy(),
        program.tags,
        events,
        program.declarations,
    )


def iter_build(program: RuleProgram, seed: int, budget: int = SLICE_BUDGET) -> Iterator[BuildSession]:
    """Yield the session after every slice (for progress/cancellation); the last yield is finished."""
    session = BuildSession(program, seed)
    while not session.step(budget):
        yield session
    yield session


def build_scene(program: RuleProgram, seed: int = 0) -> BuildResult:
    session = BuildSession(program, seed)
    while not session.step(SLICE_BUDGET):
        pass
    return BuildResult(scene_of(session), session.stats())


def build_capped(program: RuleProgram, seed: int, max_objects: int, budget: int = SLICE_BUDGET) -> SceneIR:
    """Build until the program finishes or ``max_objects`` have been emitted (thumbnails and variation grids
    only need a recognisable structure)."""
    session = BuildSession(program, seed)
    while not session.step(budget) and session.emitted < max_objects:
        pass
    return scene_of(session)
