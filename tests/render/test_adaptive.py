"""Adaptive sampling, the noise test, banded dispatch and the fair parallel lock (docs/09 §5, docs/04 §5–6)."""

from __future__ import annotations

import threading
import time
from dataclasses import replace
from functools import cache
from typing import Any

import numpy as np

from structura.compute.cpu import CpuBackend
from structura.core.build.api import build_scene
from structura.core.jit import FairLock
from structura.core.lang.api import compile_script
from structura.core.scene.ir import SceneIR
from structura.render.api import prepare, progressive, render
from structura.render.bands import Bands
from structura.render.film import active_mask, dilate, initial_mask, pixel_error
from structura.render.kernels.layout import FILM_F
from structura.render.pacing import Pacing
from structura.render.settings import RenderSettings

SCRIPT = "set background #fff\n{ s 0.6 color #888 } sphere\n"
BASE = RenderSettings(width=32, height=24, samples=64, samples_per_pass=8, integrator="path", frame=True)


@cache
def _scene() -> SceneIR:
    return build_scene(compile_script(SCRIPT).program).scene


def _film(full: tuple[float, float, float], even: tuple[float, float, float]) -> np.ndarray:
    """One pixel with 8 samples, 4 of them even."""
    return np.array([*(8 * np.array(full)), 8.0, *(4 * np.array(even)), 4.0], np.float32)


def test_pixel_error_is_zero_when_the_halves_agree_and_grows_with_their_difference() -> None:
    film = np.concatenate([_film((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)), _film((0.5, 0.5, 0.5), (0.6, 0.5, 0.4)),
                           np.zeros(FILM_F, np.float32)])  # fmt: skip
    error = pixel_error(film, 3, 1)[0]
    assert error[0] == 0.0 and error[1] > 0.1 and error[2] == 0.0  # unsampled pixels are not "noisy"
    assert list(active_mask(film, 3, 1, 0.05)) == [1, 1, 1]  # the noisy pixel's neighbours stay on


def test_masks() -> None:
    mask = np.zeros((5, 5), bool)
    mask[2, 2] = True
    assert dilate(mask).sum() == 9 and dilate(mask, 2).sum() == 25
    region = initial_mask(6, 4, (1, 1, 3, 2)).reshape(4, 6)
    assert region.sum() == 2 and region[1, 1] == region[1, 2] == 1
    assert initial_mask(6, 4).all() and initial_mask(6, 4, (3, 0, 3, 4)).all()  # empty region: everything


def test_adaptive_sampling_spends_samples_where_the_noise_is() -> None:
    adaptive = render(prepare(_scene()), replace(BASE, noise_threshold=0.02), CpuBackend())
    uniform = render(prepare(_scene()), BASE, CpuBackend())
    assert adaptive.sample_map is not None and uniform.sample_map is not None
    assert np.all(uniform.sample_map == 64)
    background = adaptive.sample_map[0, 0]
    assert background == BASE.adaptive_min_samples  # a constant background converges at once
    assert adaptive.sample_map.max() == 64 and adaptive.sample_map.mean() < 48
    assert abs(float(adaptive.image.mean()) - float(uniform.image.mean())) < 0.02


def test_time_limit_stops_after_the_pass_that_crosses_it() -> None:
    passes = list(progressive(prepare(_scene()), replace(BASE, time_limit=1e-9), CpuBackend()))
    assert len(passes) == 1 and passes[0].samples == 8 and passes[0].active == 0.0


class _Recorder:
    def __init__(self, seconds_per_row: float) -> None:
        self.rows: list[tuple[int, int]] = []
        self.row0, self.grid, self.per_row = 0, (0, 0, 0), seconds_per_row

    def update(self, **args: Any) -> None:
        self.row0 = args["row0"]

    def set_grid(self, grid: tuple[int, int, int]) -> None:
        self.grid = grid

    def dispatch(self) -> None:
        time.sleep(self.per_row * self.grid[1])
        self.rows.append((self.row0, self.grid[1]))

    def finish(self) -> None:
        pass


def test_bands_cover_every_row_once_and_adapt_to_the_dispatch_time() -> None:
    bands, fake, calls = Bands(16, 200), _Recorder(0.01), []
    bands.dispatch(fake, lambda: calls.append(1))  # type: ignore[arg-type]
    covered = [y for row0, rows in fake.rows for y in range(row0, row0 + rows)]
    assert covered == list(range(200)) and len(calls) == len(fake.rows)
    assert fake.rows[0][1] == 32 and min(rows for _, rows in fake.rows[1:-1]) <= 8  # 10 ms a row: shrink
    fast = _Recorder(0.0)
    Bands(16, 1000).dispatch(fast)  # type: ignore[arg-type]
    assert len(fast.rows) <= 4  # instant dispatches grow to the whole image


def test_auto_passes_grow_with_the_device_speed_and_fixed_passes_do_not() -> None:
    auto = Pacing(replace(BASE, samples=1000, samples_per_pass=0))
    sizes = []
    for _ in range(5):
        sizes.append(auto.next(sum(sizes)))
        auto.observe(sizes[-1], 0.001 * sizes[-1])  # a fast device: 1 ms a sample
    assert sizes == [1, 4, 16, 64, 64]
    auto.observe(64, 6.4)  # a heavy scene: 100 ms a sample
    assert auto.next(0) == 4
    fixed = Pacing(BASE)
    fixed.observe(8, 0.001)
    assert fixed.next(0) == 8 and fixed.next(60) == 4  # the last pass stops at settings.samples


def test_auto_adaptive_passes_stop_at_the_minimum_before_the_noise_test() -> None:
    pacing = Pacing(replace(BASE, samples_per_pass=0, noise_threshold=0.05))
    pacing.observe(1, 1e-6)
    pacing.observe(4, 1e-6)
    assert pacing.next(0) == BASE.adaptive_min_samples and pacing.next(10) == BASE.adaptive_min_samples - 10
    adaptive = render(prepare(_scene()), replace(BASE, samples_per_pass=0, noise_threshold=0.05), CpuBackend())
    assert adaptive.sample_map.min() >= BASE.adaptive_min_samples


def test_fair_lock_serves_waiting_threads_first() -> None:
    lock, order = FairLock(), []
    lock.__enter__()
    waiter = threading.Thread(target=lambda: (lock.__enter__(), order.append("waiter"), lock.__exit__()))
    waiter.start()
    while lock._next_ticket < 2:  # the waiter holds a ticket
        time.sleep(0.001)
    lock.__exit__()
    with lock:  # re-acquiring at once queues behind the waiter
        order.append("owner")
    waiter.join()
    assert order == ["waiter", "owner"]
