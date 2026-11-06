"""Struct-of-arrays buffers shared by the builder kernel and its Python driver (docs/06 §10.2).

Numba receives these as namedtuples of numpy arrays. Capacity is grown by the driver when the kernel
reports that a buffer is full; the kernel itself never allocates per rule application.
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np

ABSENT = np.int32(-(2**31))  # "rule not in the depth map"

# ctl (int64) slots
ST_STATUS, ST_GEN, ST_OBJECTS, ST_MAXGEN, ST_MAXOBJ, ST_SYNC, ST_INITSEED = 0, 1, 2, 3, 4, 5, 6
ST_CURLEN, ST_NEXTLEN, ST_CURSOR, ST_CUR_A, ST_POOL, ST_NOUT, ST_NAUX = 7, 8, 9, 10, 11, 12, 13
ST_NEV, ST_ERROR, ST_MAXTERM, ST_MINTERM, ST_SEEDCHG, ST_NEWSEED, ST_GENOPEN = 14, 15, 16, 17, 18, 19, 20
ST_SYNCSEED, ST_DFS, ST_APPLIED, ST_NEED = 21, 22, 23, 24
CTL_SIZE = 32
# ctl_f (float64) slots
CF_MINDIM, CF_MAXDIM = 0, 1

# status codes
RUNNING, DONE, NEED_STATE, NEED_OUT, ERROR = 0, 1, 2, 3, 4


# Packed state rows (docs/06 §10.2). Float row: matrix (16), hsv (3), alpha, then — only when the program
# uses 'mesh' — the previous frame's matrix (16), hsv (3) and alpha. Int row: rule, source action,
# generation, has-previous flag, seed, inherited material tag (v2 'mat'; 0 = none), then one depth slot per
# depth-limited rule.
F_M, F_HSV, F_ALPHA, F_PM, F_PHSV, F_PALPHA = 0, 16, 19, 20, 36, 39
F_WIDTH, F_WIDTH_MESH = 20, 40
I_RULE, I_SRC, I_GEN, I_HASPREV, I_SEED, I_MAT, I_DEPTH = 0, 1, 2, 3, 4, 5, 6


class StateBuf(NamedTuple):
    f: np.ndarray  # float32[C, 20 or 40]
    i: np.ndarray  # int64[C, I_DEPTH + slots]


class OutBuf(NamedTuple):
    kind: np.ndarray  # int8[N] primitive kind (docs/07 §2.2 mapping applied later)
    xf: np.ndarray  # float32[N,12] translation, then the linear columns of the state matrix
    rgba: np.ndarray  # float32[N,4]
    tag: np.ndarray  # int32[N]
    src: np.ndarray  # int32[N]
    gen: np.ndarray  # int32[N]
    aux: np.ndarray  # int32[N] row in aux_f or -1
    aux_f: np.ndarray  # float32[M,13] mesh: prev base,d1,d2 (9) + prev rgba (4); triangle: p1,p2,p3 (9);
    #                    cone / torus / tube: the bracket parameter (1)
    events: np.ndarray  # int32[E,3] (event index, generation, primitives emitted before it)


def state_buffer(capacity: int, slots: int, mesh: bool) -> StateBuf:
    c = max(1, capacity)
    ints = np.zeros((c, I_DEPTH + max(1, slots)), np.int64)
    ints[:, I_DEPTH:] = ABSENT
    ints[:, I_SRC] = -1
    return StateBuf(np.zeros((c, F_WIDTH_MESH if mesh else F_WIDTH), np.float32), ints)


def out_buffer(capacity: int, aux: int, events: int) -> OutBuf:
    n = max(1, capacity)
    return OutBuf(
        np.zeros(n, np.int8),
        np.zeros((n, 12), np.float32),
        np.zeros((n, 4), np.float32),
        np.zeros(n, np.int32),
        np.zeros(n, np.int32),
        np.zeros(n, np.int32),
        np.full(n, -1, np.int32),
        np.zeros((max(1, aux), 13), np.float32),
        np.zeros((max(1, events), 3), np.int32),
    )


def grow(buf: StateBuf, used: int, capacity: int) -> StateBuf:
    """Copy the first ``used`` rows into a buffer with ``capacity`` rows (new rows: depth ABSENT)."""
    f = np.zeros((capacity, buf.f.shape[1]), np.float32)
    i = np.zeros((capacity, buf.i.shape[1]), np.int64)
    i[:, I_DEPTH:] = ABSENT
    f[:used], i[:used] = buf.f[:used], buf.i[:used]
    return StateBuf(f, i)


def _resized(arr: np.ndarray, used: int, capacity: int) -> np.ndarray:
    new = np.zeros((capacity, *arr.shape[1:]), arr.dtype)
    new[:used] = arr[:used]
    return new


def grow_out(out: OutBuf, n: int, n_aux: int, n_ev: int, cap: int, cap_aux: int, cap_ev: int) -> OutBuf:
    return OutBuf(
        _resized(out.kind, n, cap),
        _resized(out.xf, n, cap),
        _resized(out.rgba, n, cap),
        _resized(out.tag, n, cap),
        _resized(out.src, n, cap),
        _resized(out.gen, n, cap),
        _resized(out.aux, n, cap),
        _resized(out.aux_f, n_aux, cap_aux),
        _resized(out.events, n_ev, cap_ev),
    )
