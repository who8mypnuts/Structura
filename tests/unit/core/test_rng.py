"""MT19937 draws (docs/05 §7) — the stream must equal numpy's legacy-seeded MT19937."""

from __future__ import annotations

import numpy as np
import pytest

from structura.core.rng import mt_get_double, mt_get_int, mt_get_int_n, mt_new


@pytest.mark.parametrize("seed", [0, 1, 42, 5489, -7, 2**31 + 5, 2**32 - 1])
def test_stream_matches_numpy(seed: int) -> None:
    ours = mt_new(seed)
    ref = np.random.RandomState(seed & 0xFFFFFFFF)._bit_generator
    assert [int(mt_get_int(ours)) for _ in range(1500)] == [int(ref.random_raw()) for _ in range(1500)]


def test_get_double_is_closed_interval_scaling() -> None:
    a, b = mt_new(9), mt_new(9)
    assert mt_get_double(a) == pytest.approx(int(mt_get_int(b)) / 4294967295.0, abs=0)


def test_get_int_n_masks_and_rejects() -> None:
    a, b = mt_new(11), mt_new(11)
    for _ in range(200):
        value = mt_get_int_n(a, 359)
        while True:
            raw = int(mt_get_int(b)) & 511
            if raw <= 359:
                break
        assert value == raw


def test_cpu_thread_preference_applies_inside_parallel_sections() -> None:
    import numba  # noqa: PLC0415

    from structura.core.jit import parallel_section, set_cpu_threads  # noqa: PLC0415

    set_cpu_threads(1)
    try:
        with parallel_section():
            assert numba.get_num_threads() == 1
    finally:
        set_cpu_threads(0)
    with parallel_section():
        assert numba.get_num_threads() == numba.config.NUMBA_NUM_THREADS
