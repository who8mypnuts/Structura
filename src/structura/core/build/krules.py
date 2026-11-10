"""Kernel: rule application, actions, primitive emission and set-commands (docs/05 §4.4–§6, docs/06 §10).

``work`` is the 2-entry work buffer: work[0] is the builder's current state, work[1] the child being constructed.
``children`` receives child states, ``outbuf`` primitives and events; ``ctl``/``ctl_f`` are the control words.
"""

from __future__ import annotations

import numpy as np

from structura.core.jit import kernel

from ..rng.mt19937 import mt_get_double, mt_get_int, mt_seed
from .kmath import F0, F1, hsv_to_rgb32, mat_vec
from .kstate import apply_xf, copy_entry
from .layout import (
    ABSENT,
    CF_MAXDIM,
    CF_MINDIM,
    ERROR,
    F_ALPHA,
    F_HSV,
    F_M,
    F_PALPHA,
    F_PHSV,
    F_PM,
    F_WIDTH_MESH,
    I_DEPTH,
    I_GEN,
    I_HASPREV,
    I_MAT,
    I_RULE,
    I_SEED,
    I_SRC,
    NEED_OUT,
    RUNNING,
    ST_DFS,
    ST_ERROR,
    ST_INITSEED,
    ST_MAXGEN,
    ST_MAXOBJ,
    ST_NAUX,
    ST_NEED,
    ST_NEV,
    ST_NEWSEED,
    ST_NOUT,
    ST_OBJECTS,
    ST_POOL,
    ST_SEEDCHG,
    ST_SYNC,
)

RULE_CUSTOM, RULE_AMBIGUOUS = 0, 1
PRIM_MESH, PRIM_TEMPLATE, PRIM_TRIANGLE = 3, 7, 8  # catalog ids (v1's cylinder, id 2, is drawn like v2's)
PRIM_CONE, PRIM_TORUS, PRIM_TUBE = 10, 11, 13  # v2 primitives with a bracket parameter (catalog ids)
OP_EVENT, OP_ERROR, OP_MAXDEPTH, OP_MAXOBJECTS, OP_MINSIZE, OP_MAXSIZE = 1, 2, 3, 4, 5, 6
OP_SEED_INT, OP_SEED_INITIAL, OP_SYNCRANDOM, OP_COLORPOOL = 7, 8, 9, 10
MAX_RETIREMENT_CHAIN = 100000


@kernel
def set_rules_maxdepth(tables, md: np.ndarray, value: int) -> None:  # type: ignore[no-untyped-def]
    """Structure Synth's RuleSet::setRulesMaxDepth: only listed rules; ambiguous rules overwrite all
    alternatives (they never record a depth of their own)."""
    for r in range(md.shape[0]):
        if tables.rule_listed[r] == 0 or md[r] > 0:
            continue
        if tables.rule_kind[r] == RULE_AMBIGUOUS:
            start, count = tables.rule_alt[r, 0], tables.rule_alt[r, 1]
            for k in range(start, start + count):
                md[tables.alts[k]] = value
        else:
            md[r] = value


@kernel
def _limits_op(tables, op: int, ctl, ctl_f, md) -> None:  # type: ignore[no-untyped-def]
    code, value = tables.setop_code[op], tables.setop_i[op]
    if code == OP_MAXDEPTH:
        ctl[ST_MAXGEN] = value
        if ctl[ST_DFS] == 1 and value > 0:
            set_rules_maxdepth(tables, md, value)
    elif code == OP_MAXOBJECTS:
        ctl[ST_MAXOBJ] = value
    elif code == OP_MINSIZE:
        ctl_f[CF_MINDIM] = tables.setop_f[op]
    elif code == OP_MAXSIZE:
        ctl_f[CF_MAXDIM] = tables.setop_f[op]


@kernel
def exec_setop(tables, op: int, work, outbuf, ctl, ctl_f, md, geo, col) -> int:  # type: ignore[no-untyped-def]
    code, value = tables.setop_code[op], tables.setop_i[op]
    if code == OP_EVENT:
        e = ctl[ST_NEV]
        if e >= outbuf.events.shape[0]:
            ctl[ST_NEED] = 1
            return NEED_OUT
        outbuf.events[e, 0], outbuf.events[e, 1], outbuf.events[e, 2] = value, work.i[0, I_GEN], ctl[ST_NOUT]
        ctl[ST_NEV] = e + 1
    elif code == OP_ERROR:
        ctl[ST_ERROR] = value
        return ERROR
    elif code == OP_SEED_INT:
        mt_seed(geo, value)
        mt_seed(col, value)
        ctl[ST_SEEDCHG], ctl[ST_NEWSEED] = 1, value
    elif code == OP_SEED_INITIAL:
        if ctl[ST_INITSEED] == 0:
            ctl[ST_INITSEED] = np.int64(np.int32(mt_get_int(geo)))
        work.i[0, I_SEED] = ctl[ST_INITSEED]
    elif code == OP_SYNCRANDOM:
        ctl[ST_SYNC] = value
    elif code == OP_COLORPOOL:
        ctl[ST_POOL] = value
    else:
        _limits_op(tables, op, ctl, ctl_f, md)
    return RUNNING


@kernel
def _vectors(f: np.ndarray, off: int, out: np.ndarray, n: int, axes: int) -> None:
    """out[n] = base, d1, d2[, d3] exactly as Structure Synth derives them: M·e − M·0."""
    bx, by, bz = mat_vec(f, 0, off, F0, F0, F0)
    out[n, 0], out[n, 1], out[n, 2] = bx, by, bz
    for k in range(axes):
        ex, ey, ez = mat_vec(f, 0, off, F1 if k == 0 else F0, F1 if k == 1 else F0, F1 if k == 2 else F0)
        out[n, 3 + 3 * k], out[n, 4 + 3 * k], out[n, 5 + 3 * k] = ex - bx, ey - by, ez - bz


@kernel
def _matrix(f: np.ndarray, off: int, out: np.ndarray, n: int) -> None:
    """out[n] = translation, then the three linear columns of the state matrix (exact, not M·e − M·0)."""
    for i in range(3):
        out[n, i] = f[0, off + 4 * i + 3]
        for k in range(3):
            out[n, 3 + 3 * k + i] = f[0, off + 4 * i + k]


@kernel
def has_param(prim: int) -> bool:
    return prim == PRIM_CONE or prim == PRIM_TORUS or prim == PRIM_TUBE


@kernel
def _aux_row(tables, r: int, work, outbuf, row: int) -> None:  # type: ignore[no-untyped-def]
    """Mesh: previous frame (base, d1, d2) + previous colour. Triangle: world corners. Cone, torus, tube: the
    bracket parameter."""
    f = work.f
    if has_param(tables.rule_prim[r]):
        outbuf.aux_f[row, 0] = tables.rule_param[r]
        return
    if tables.rule_prim[r] == PRIM_MESH:
        _vectors(f, F_PM, outbuf.aux_f, row, 2)
        pr, pg, pb = hsv_to_rgb32(f[0, F_PHSV], f[0, F_PHSV + 1], f[0, F_PHSV + 2])
        outbuf.aux_f[row, 9], outbuf.aux_f[row, 10], outbuf.aux_f[row, 11], outbuf.aux_f[row, 12] = (
            pr,
            pg,
            pb,
            f[0, F_PALPHA],
        )
        return
    t = tables.rule_tri[r]
    for k in range(3):
        x, y, z = mat_vec(f, 0, F_M, tables.tri_p[t, k, 0], tables.tri_p[t, k, 1], tables.tri_p[t, k, 2])
        outbuf.aux_f[row, 3 * k], outbuf.aux_f[row, 3 * k + 1], outbuf.aux_f[row, 3 * k + 2] = x, y, z


@kernel
def emit(tables, r: int, work, outbuf, ctl) -> int:  # type: ignore[no-untyped-def]
    """Counts and writes the object that rule ``r`` makes.

    Templates count nothing; a mesh without a previous frame is counted but not drawn, as in Structure Synth 1.5;
    v1 cylinders are drawn (1.5 drew nothing for them).

    Args:
        tables: The compiled rule tables.
        r: The primitive rule's index.
        work: The current state (its frame, colour and flags).
        outbuf: The output rows.
        ctl: The build's control counters (objects, status).

    Returns:
        RUNNING: emitting never ends the build (limits are checked per generation).
    """
    prim = tables.rule_prim[r]
    if prim != PRIM_TEMPLATE:
        ctl[ST_OBJECTS] += 1
        if prim == PRIM_MESH and work.i[0, I_HASPREV] == 0:
            return RUNNING  # counted, but Structure Synth 1.5 draws nothing (a mesh needs a previous frame)
    n, f = ctl[ST_NOUT], work.f
    tag = tables.rule_tag[r]
    outbuf.kind[n], outbuf.tag[n], outbuf.src[n], outbuf.gen[n], outbuf.aux[n] = (
        prim,
        tag if tag != 0 else work.i[0, I_MAT],  # an explicit tag beats the inherited v2 'mat'
        work.i[0, I_SRC],
        work.i[0, I_GEN],
        -1,
    )
    _matrix(f, F_M, outbuf.xf, n)
    red, green, blue = hsv_to_rgb32(f[0, F_HSV], f[0, F_HSV + 1], f[0, F_HSV + 2])
    outbuf.rgba[n, 0], outbuf.rgba[n, 1], outbuf.rgba[n, 2], outbuf.rgba[n, 3] = red, green, blue, f[0, F_ALPHA]
    if prim == PRIM_MESH or prim == PRIM_TRIANGLE or has_param(prim):
        _aux_row(tables, r, work, outbuf, ctl[ST_NAUX])
        outbuf.aux[n] = ctl[ST_NAUX]
        ctl[ST_NAUX] += 1
    ctl[ST_NOUT] = n + 1
    return RUNNING


@kernel
def _new_child(work, children, n: int, target: int, action: int, slot: int, depth: int, with_prev: bool) -> None:  # type: ignore[no-untyped-def]
    """children[n] ← copy of the builder state work[0], prepared as a child (built in place: no extra copy)."""
    copy_entry(work, 0, children, n)
    if with_prev and children.f.shape[1] >= F_WIDTH_MESH:
        for k in range(16):
            children.f[n, F_PM + k] = work.f[0, F_M + k]
        for k in range(4):
            children.f[n, F_PHSV + k] = work.f[0, F_HSV + k]  # hsv (3) + alpha
        children.i[n, I_HASPREV] = 1
    if slot >= 0:
        children.i[n, I_DEPTH + slot] = depth
    children.i[n, I_RULE], children.i[n, I_SRC], children.i[n, I_GEN] = target, action, work.i[0, I_GEN] + 1


@kernel
def apply_call(  # type: ignore[no-untyped-def]
    tables, a: int, calling: int, depth: int, work, children, n_len: int, col, pool: int, counters, tmp
) -> int:
    """Push every child produced by call action ``a``; returns the new child count (docs/05 §4.4)."""
    start, nloops = tables.act_loops[a, 0], tables.act_loops[a, 1]
    slot = tables.rule_slot[calling] if calling >= 0 else -1
    target = tables.act_target[a]
    if nloops == 0:
        _new_child(work, children, n_len, target, a, slot, depth, False)
        return n_len + 1
    for i in range(nloops):
        counters[i] = 1
    while True:
        _new_child(work, children, n_len, target, a, slot, depth, True)
        for i in range(nloops):
            for _ in range(counters[i]):
                apply_xf(tables, tables.loop_xf[start + i], children, n_len, col, pool, tmp)
        n_len += 1
        counters[0] += 1
        for i in range(nloops):
            if counters[i] > tables.loop_reps[start + i]:
                if i == nloops - 1:
                    return n_len
                counters[i] = 1
                counters[i + 1] += 1


@kernel
def _pick_alternative(tables, r: int, geo: np.ndarray) -> int:  # type: ignore[no-untyped-def]
    start, count = tables.rule_alt[r, 0], tables.rule_alt[r, 1]
    total = 0.0
    for k in range(start, start + count):
        total += tables.rule_weight[tables.alts[k]]
    chosen = total * mt_get_double(geo)
    acc = 0.0
    for k in range(start, start + count):
        acc += tables.rule_weight[tables.alts[k]]
        if chosen <= acc:
            return tables.alts[k]
    return tables.alts[start + count - 1]


@kernel
def _depth_for(tables, r: int, work, md: np.ndarray):  # type: ignore[no-untyped-def]
    """(decision, new depth) for custom rule r: decision 0 = apply, 1 = retire, 2 = stop."""
    if md[r] == -1:
        return 0, 0
    slot = tables.rule_slot[r]
    current = work.i[0, I_DEPTH + slot] if slot >= 0 else ABSENT
    if current == ABSENT:
        return 0, md[r] - 1
    if current <= 0:
        return (1 if tables.rule_retire[r] >= 0 else 2), 0
    return 0, current - 1


@kernel
def _apply_actions(tables, r, depth, work, children, n_len, outbuf, ctl, ctl_f, md, geo, col, counters, tmp):  # type: ignore[no-untyped-def]
    calling = r if md[r] != -1 else -1
    start, count = tables.rule_act[r, 0], tables.rule_act[r, 1]
    for a in range(start, start + count):
        if tables.act_kind[a] == 1:
            status = exec_setop(tables, tables.act_setop[a], work, outbuf, ctl, ctl_f, md, geo, col)
            if status != RUNNING:
                return status, n_len
        else:
            n_len = apply_call(tables, a, calling, depth, work, children, n_len, col, ctl[ST_POOL], counters, tmp)
    return RUNNING, n_len


@kernel
def apply_rule(tables, r: int, work, children, n_start: int, outbuf, ctl, ctl_f, md, geo, col, counters, tmp):  # type: ignore[no-untyped-def]
    """Apply rule r to work[0]; child states go to ``children`` from n_start. Returns (status, child count)."""
    for _ in range(MAX_RETIREMENT_CHAIN):
        kind = tables.rule_kind[r]
        if kind == RULE_AMBIGUOUS:
            r = _pick_alternative(tables, r, geo)
            continue
        if kind != RULE_CUSTOM:
            return emit(tables, r, work, outbuf, ctl), n_start
        decision, depth = _depth_for(tables, r, work, md)
        if decision == 2:
            return RUNNING, n_start
        if decision == 1:
            work.i[0, I_DEPTH + tables.rule_slot[r]] = md[r]
            r = tables.rule_retire[r]
            continue
        return _apply_actions(
            tables, r, depth, work, children, n_start, outbuf, ctl, ctl_f, md, geo, col, counters, tmp
        )
    ctl[ST_ERROR] = -1
    return ERROR, n_start
