"""MT19937 (Matsumoto & Nishimura) with the draw functions Structure Synth uses.

State layout: a uint32 array of 625 words — 624 words of generator state followed by the read index.
All functions are Numba-jitted so the builder kernel can call them directly.

Draw semantics (docs/05-eisenscript-language.md §7):
  get_int()      -> raw 32-bit output
  get_double()   -> get_int() / 4294967295.0          (closed interval [0, 1])
  get_int_n(n)   -> smallest all-ones mask >= n; draw masked values until one is <= n
  seed(s)        -> standard init_genrand(s mod 2**32)
"""

from __future__ import annotations

import numpy as np

from structura.core.jit import kernel

N = 624
M = 397
MT_STATE_SIZE = N + 1
MATRIX_A = np.uint32(0x9908B0DF)
UPPER = np.uint32(0x80000000)
LOWER = np.uint32(0x7FFFFFFF)


@kernel
def mt_seed(state: np.ndarray, seed: int) -> None:
    state[0] = np.uint32(seed & 0xFFFFFFFF)
    for i in range(1, N):
        prev = np.uint64(state[i - 1])
        state[i] = np.uint32(
            (np.uint64(1812433253) * (prev ^ (prev >> np.uint64(30))) + np.uint64(i)) & np.uint64(0xFFFFFFFF)
        )
    state[N] = np.uint32(N)  # force a reload on the next draw


def mt_new(seed: int = 0) -> np.ndarray:
    state = np.zeros(MT_STATE_SIZE, dtype=np.uint32)
    mt_seed(state, seed)
    return state


@kernel
def _twist(state: np.ndarray) -> None:
    for i in range(N):
        y = (state[i] & UPPER) | (state[(i + 1) % N] & LOWER)
        v = state[(i + M) % N] ^ (y >> np.uint32(1))
        if y & np.uint32(1):
            v ^= MATRIX_A
        state[i] = v
    state[N] = np.uint32(0)


@kernel
def mt_get_int(state: np.ndarray) -> np.uint32:
    if state[N] >= np.uint32(N):
        _twist(state)
    y = state[state[N]]
    state[N] += np.uint32(1)
    y ^= y >> np.uint32(11)
    y ^= (y << np.uint32(7)) & np.uint32(0x9D2C5680)
    y ^= (y << np.uint32(15)) & np.uint32(0xEFC60000)
    y ^= y >> np.uint32(18)
    return y


@kernel
def mt_get_double(state: np.ndarray) -> float:
    return float(mt_get_int(state)) * (1.0 / 4294967295.0)


@kernel
def mt_get_int_n(state: np.ndarray, n: int) -> int:
    used = np.uint32(n)
    used |= used >> np.uint32(1)
    used |= used >> np.uint32(2)
    used |= used >> np.uint32(4)
    used |= used >> np.uint32(8)
    used |= used >> np.uint32(16)
    while True:
        i = mt_get_int(state) & used
        if i <= np.uint32(n):
            return int(i)
