"""Python driver for the builder kernel: buffer management, slicing, results (docs/06 §10)."""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

from ..errors import BuildError
from ..lang.compile.program import RuleProgram
from ..rng.mt19937 import mt_new
from . import layout
from .krules import set_rules_maxdepth
from .kstep import step_bfs, step_dfs
from .limits import application_limits

PRIM_MESH = 3
DEFAULT_MAX_GENERATIONS = 1000
DEFAULT_MAX_OBJECTS = 100_000


@dataclass(frozen=True)
class BuildStats:
    objects: int
    emitted: int
    generations: int
    applications: int
    max_size_culled: int
    min_size_culled: int
    max_generations: int
    max_objects: int
    seed_changed: bool
    new_seed: int
    depth_first: bool
    seconds: float


def uses_mesh(program: RuleProgram) -> bool:
    """True if any action or retirement can reach the 'mesh' primitive (previous frames must be stored)."""
    targets = set(program.act_target[program.act_kind == 0].tolist()) | set(program.rule_retire.tolist())
    return any(t >= 0 and program.rule_prim[t] == PRIM_MESH for t in targets)


class BuildSession:
    """A resumable build. Call :meth:`step` until it returns ``True`` (finished)."""

    def __init__(self, program: RuleProgram, seed: int) -> None:
        self.program, self.started = program, time.perf_counter()
        self.tables = program.kernel_tables()
        slots, mesh = program.n_slots, uses_mesh(program)
        self.buf_a, self.buf_b = layout.state_buffer(1024, slots, mesh), layout.state_buffer(1024, slots, mesh)
        self.work = layout.state_buffer(2, slots, mesh)
        self.outbuf = layout.out_buffer(4096, 256, 64)
        self.ctl = np.zeros(layout.CTL_SIZE, np.int64)
        self.ctl_f = np.zeros(2, np.float64)
        self.md = program.rule_maxdepth.astype(np.int64).copy()
        self.geo, self.col = mt_new(seed), mt_new(seed)
        self.counters = np.ones(max(1, int(program.act_loops[:, 1].max(initial=1))), np.int64)
        self.tmp = np.zeros(16, np.float32)
        self.limits = application_limits(program)
        self._init_root()

    def _init_root(self) -> None:
        buf_a, ctl = self.buf_a, self.ctl
        buf_a.i[0, layout.I_RULE] = self.program.top
        buf_a.f[0, layout.F_M : layout.F_M + 16] = np.eye(4, dtype=np.float32).ravel()
        buf_a.f[0, layout.F_HSV : layout.F_HSV + 3], buf_a.f[0, layout.F_ALPHA] = (0.0, 1.0, 1.0), 1.0
        ctl[layout.ST_CURLEN], ctl[layout.ST_CUR_A] = 1, 1
        ctl[layout.ST_MAXGEN], ctl[layout.ST_MAXOBJ] = DEFAULT_MAX_GENERATIONS, DEFAULT_MAX_OBJECTS
        ctl[layout.ST_DFS] = int(self.program.depth_first)
        if self.program.depth_first:
            set_rules_maxdepth(self.tables, self.md, DEFAULT_MAX_GENERATIONS)

    # ---------------------------------------------------------------------------------------------------
    def step(self, budget: int = 20_000) -> bool:
        kernel = step_dfs if self.program.depth_first else step_bfs
        while True:
            status = kernel(
                self.tables,
                self.buf_a,
                self.buf_b,
                self.work,
                self.outbuf,
                self.ctl,
                self.ctl_f,
                self.md,
                self.geo,
                self.col,
                self.counters,
                self.tmp,
                self.limits,
                budget,
            )
            if status == layout.NEED_STATE:
                self._grow_states()
            elif status == layout.NEED_OUT:
                self._grow_out()
            elif status == layout.ERROR:
                raise BuildError(self._error_message())
            else:
                return status == layout.DONE

    def _grow_states(self) -> None:
        need = int(max(self.ctl[layout.ST_NEED], self.buf_a.i.shape[0] * 2))
        self.buf_a = layout.grow(self.buf_a, self.buf_a.i.shape[0], need)
        self.buf_b = layout.grow(self.buf_b, self.buf_b.i.shape[0], need)
        self.ctl[layout.ST_NEED] = 0

    def _grow_out(self) -> None:
        outbuf, ctl = self.outbuf, self.ctl
        self.outbuf = layout.grow_out(
            outbuf,
            int(ctl[layout.ST_NOUT]),
            int(ctl[layout.ST_NAUX]),
            int(ctl[layout.ST_NEV]),
            outbuf.kind.shape[0] * 2,
            outbuf.aux_f.shape[0] * 2,
            max(outbuf.events.shape[0] * 2, int(ctl[layout.ST_NEV] + self.limits[:, 1].max() + 1)),
        )

    def _error_message(self) -> str:
        index = int(self.ctl[layout.ST_ERROR])
        if index < 0:
            return "Rule retirement chain did not terminate."
        return self.program.errors[index]

    # ---------------------------------------------------------------------------------------------------
    @property
    def emitted(self) -> int:
        return int(self.ctl[layout.ST_NOUT])

    def memory_bytes(self) -> int:
        """Bytes held by the state and output buffers (each grows by doubling)."""
        total = 0
        for buffer in (self.buf_a, self.buf_b, self.work, self.outbuf):
            total += sum(v.nbytes for v in buffer if isinstance(v, np.ndarray))  # NamedTuples of arrays
        return total

    def stats(self) -> BuildStats:
        c = self.ctl
        return BuildStats(
            int(c[layout.ST_OBJECTS]),
            int(c[layout.ST_NOUT]),
            int(c[layout.ST_GEN]),
            int(c[layout.ST_APPLIED]),
            int(c[layout.ST_MAXTERM]),
            int(c[layout.ST_MINTERM]),
            int(c[layout.ST_MAXGEN]),
            int(c[layout.ST_MAXOBJ]),
            bool(c[layout.ST_SEEDCHG]),
            int(c[layout.ST_NEWSEED]),
            self.program.depth_first,
            time.perf_counter() - self.started,
        )
