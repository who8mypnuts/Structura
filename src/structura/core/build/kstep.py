"""Kernel: resumable breadth-first and depth-first expansion loops (docs/05 §5, docs/06 §10.1).

Each call processes at most ``budget`` rule applications and returns a status. Before every application the
kernel checks that the receiving buffers can hold the worst case for that rule (``max_children``, one output
row, ``max_events``); if not it returns NEED_STATE/NEED_OUT *without* touching any state, so the Python driver
can grow the buffers and call again.
"""

from __future__ import annotations

import numpy as np

from structura.core.jit import kernel

from ..rng.mt19937 import mt_get_int, mt_seed
from .kmath import F0, F1, length32, mat_vec
from .krules import apply_rule
from .kstate import copy_entry
from .layout import (
    CF_MAXDIM,
    CF_MINDIM,
    DONE,
    F_M,
    I_RULE,
    I_SEED,
    NEED_OUT,
    NEED_STATE,
    RUNNING,
    ST_APPLIED,
    ST_CUR_A,
    ST_CURLEN,
    ST_CURSOR,
    ST_GEN,
    ST_GENOPEN,
    ST_MAXGEN,
    ST_MAXOBJ,
    ST_MAXTERM,
    ST_MINTERM,
    ST_NAUX,
    ST_NEED,
    ST_NEV,
    ST_NEXTLEN,
    ST_NOUT,
    ST_OBJECTS,
    ST_STATUS,
    ST_SYNC,
    ST_SYNCSEED,
)


@kernel
def _culled(work, ctl, ctl_f) -> bool:  # type: ignore[no-untyped-def]
    """minsize/maxsize: length of M·(1,1,1) − M·(0,0,0) (only evaluated if a limit is set)."""
    if ctl_f[CF_MAXDIM] == 0.0 and ctl_f[CF_MINDIM] == 0.0:
        return False
    x1, y1, z1 = mat_vec(work.f, 0, F_M, F1, F1, F1)
    x0, y0, z0 = mat_vec(work.f, 0, F_M, F0, F0, F0)
    size = length32(x1 - x0, y1 - y0, z1 - z0)
    if ctl_f[CF_MAXDIM] != 0.0 and size > np.float32(ctl_f[CF_MAXDIM]):
        ctl[ST_MAXTERM] += 1
        return True
    if ctl_f[CF_MINDIM] != 0.0 and size < np.float32(ctl_f[CF_MINDIM]):
        ctl[ST_MINTERM] += 1
        return True
    return False


@kernel
def _room(ctl, rule: int, n_len: int, n_cap: int, out_cap: int, aux_cap: int, ev_cap: int, limits) -> int:  # type: ignore[no-untyped-def]
    """limits[r] = (max children, max events) of one application of rule r."""
    if n_len + limits[rule, 0] > n_cap:
        ctl[ST_NEED] = n_len + limits[rule, 0]
        return NEED_STATE
    if ctl[ST_NOUT] + 1 > out_cap or ctl[ST_NAUX] + 1 > aux_cap or ctl[ST_NEV] + limits[rule, 1] > ev_cap:
        return NEED_OUT
    return RUNNING


@kernel
def _reseed(work, geo, col) -> None:  # type: ignore[no-untyped-def]
    if work.i[0, I_SEED] != 0:
        mt_seed(geo, work.i[0, I_SEED])
        mt_seed(col, work.i[0, I_SEED])
        work.i[0, I_SEED] = mt_get_int(geo)


@kernel
def _open_generation(ctl, geo) -> bool:  # type: ignore[no-untyped-def]
    n = ctl[ST_CURLEN]
    if n == 0 or ctl[ST_GEN] >= ctl[ST_MAXGEN] or ctl[ST_OBJECTS] >= ctl[ST_MAXOBJ] or n >= ctl[ST_MAXOBJ]:
        return False
    ctl[ST_SYNCSEED] = mt_get_int(geo)  # drawn every generation, even without syncrandom
    ctl[ST_GEN] += 1
    ctl[ST_CURSOR], ctl[ST_NEXTLEN], ctl[ST_GENOPEN] = 0, 0, 1
    return True


@kernel
def step_bfs(tables, buf_a, buf_b, work, outbuf, ctl, ctl_f, md, geo, col, counters, tmp, limits, budget: int) -> int:  # type: ignore[no-untyped-def]
    done = 0
    while done < budget:
        cur, nxt = (buf_a, buf_b) if ctl[ST_CUR_A] == 1 else (buf_b, buf_a)
        if ctl[ST_GENOPEN] == 0 and not _open_generation(ctl, geo):
            ctl[ST_STATUS] = DONE
            return DONE
        i = ctl[ST_CURSOR]
        if i >= ctl[ST_CURLEN]:
            ctl[ST_CUR_A], ctl[ST_CURLEN], ctl[ST_GENOPEN] = 1 - ctl[ST_CUR_A], ctl[ST_NEXTLEN], 0
            continue
        rule = cur.i[i, I_RULE]
        room = _room(
            ctl,
            rule,
            ctl[ST_NEXTLEN],
            nxt.i.shape[0],
            outbuf.kind.shape[0],
            outbuf.aux_f.shape[0],
            outbuf.events.shape[0],
            limits,
        )
        if room != RUNNING:
            ctl[ST_STATUS] = room
            return room
        copy_entry(cur, i, work, 0)
        _reseed(work, geo, col)
        if ctl[ST_SYNC] == 1:
            mt_seed(geo, ctl[ST_SYNCSEED])
            mt_seed(col, ctl[ST_SYNCSEED])
        ctl[ST_CURSOR] = i + 1
        if _culled(work, ctl, ctl_f):
            continue
        status, n_len = apply_rule(
            tables, rule, work, nxt, ctl[ST_NEXTLEN], outbuf, ctl, ctl_f, md, geo, col, counters, tmp
        )
        ctl[ST_NEXTLEN] = n_len
        ctl[ST_APPLIED] += 1
        done += 1
        if status != RUNNING:
            ctl[ST_STATUS] = status
            return status
    return RUNNING


@kernel
def step_dfs(tables, buf_a, buf_b, work, outbuf, ctl, ctl_f, md, geo, col, counters, tmp, limits, budget: int) -> int:  # type: ignore[no-untyped-def]
    """A is a stack whose top is the legacy list's front; children are pushed in reverse order."""
    done = 0
    while done < budget:
        top = ctl[ST_CURLEN] - 1
        if top < 0 or ctl[ST_OBJECTS] >= ctl[ST_MAXOBJ]:
            ctl[ST_STATUS] = DONE
            return DONE
        rule = buf_a.i[top, I_RULE]
        room = _room(
            ctl,
            rule,
            top,
            buf_a.i.shape[0],
            outbuf.kind.shape[0],
            outbuf.aux_f.shape[0],
            outbuf.events.shape[0],
            limits,
        )
        if room != RUNNING or limits[rule, 0] > buf_b.i.shape[0]:
            ctl[ST_STATUS] = NEED_STATE if room == RUNNING else room
            ctl[ST_NEED] = max(ctl[ST_NEED], limits[rule, 0])
            return ctl[ST_STATUS]
        copy_entry(buf_a, top, work, 0)
        _reseed(work, geo, col)
        ctl[ST_CURLEN] = top  # pop (also for culled states: Structure Synth 1.5 hangs, D15)
        ctl[ST_GEN] += 1
        if _culled(work, ctl, ctl_f):
            continue
        status, n_children = apply_rule(tables, rule, work, buf_b, 0, outbuf, ctl, ctl_f, md, geo, col, counters, tmp)
        for k in range(n_children - 1, -1, -1):
            copy_entry(buf_b, k, buf_a, ctl[ST_CURLEN])
            ctl[ST_CURLEN] += 1
        ctl[ST_APPLIED] += 1
        done += 1
        if status != RUNNING:
            ctl[ST_STATUS] = status
            return status
    return RUNNING
