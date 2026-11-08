"""Image samplers (docs/09 §4–5): buckets and their orders, the tiled sampler, the mosaic first image, the
Halton sequence, per-lobe bounce limits and the AO integrator's direct light."""

from __future__ import annotations

import itertools
from dataclasses import replace
from functools import cache

import numpy as np
import pytest

from structura.compute.cpu import CpuBackend
from structura.core.build.api import build_scene
from structura.core.lang.api import compile_script
from structura.core.scene.ir import SceneIR
from structura.render.api import prepare, progressive, render
from structura.render.buckets import buckets, hilbert_index
from structura.render.settings import BUCKET_ORDERS, RenderSettings

SCRIPT = "set background #fff\n{ s 0.6 color #888 } sphere\n{ x 0.8 s 0.5 color #c84 } box\n"
BASE = RenderSettings(width=40, height=24, samples=8, samples_per_pass=4, integrator="path", frame=True)


@cache
def _scene() -> SceneIR:
    return build_scene(compile_script(SCRIPT).program).scene


@pytest.mark.parametrize("order", BUCKET_ORDERS)
def test_buckets_cover_every_pixel_once(order: str) -> None:
    cover = np.zeros((37, 53), int)
    for x0, y0, x1, y1 in buckets(53, 37, 16, order, seed=3):
        cover[y0:y1, x0:x1] += 1
    assert np.all(cover == 1)


def test_hilbert_order_walks_between_neighbours() -> None:
    assert sorted(hilbert_index(4, x, y) for x in range(4) for y in range(4)) == list(range(16))
    path = buckets(64, 64, 16, "hilbert")
    steps = [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in itertools.pairwise(path)]
    assert set(steps) == {16}
    spiral = buckets(80, 80, 16, "spiral")
    assert spiral[0] == (32, 32, 48, 48)  # the centre first


def test_the_tiled_sampler_gives_the_progressive_image() -> None:
    prepared = prepare(_scene())
    flat = render(prepared, BASE, CpuBackend())
    snapshots = list(progressive(prepared, replace(BASE, sampler="tiled", bucket_size=16), CpuBackend()))
    last = snapshots[-1]
    assert last.completed == 1.0 and last.tile is None and last.samples == BASE.samples
    assert np.allclose(last.image, flat.image, atol=1e-4)


def test_tiled_adaptive_sampling_stops_converged_pixels() -> None:
    settings = replace(BASE, samples=64, noise_threshold=0.05, adaptive_min_samples=8, sampler="tiled", bucket_size=8)
    last = render(prepare(_scene()), settings, CpuBackend())
    assert last.sample_map is not None and last.sample_map.min() >= 8 and last.sample_map.min() < 64


def test_the_mosaic_comes_first_and_changes_nothing() -> None:
    prepared = prepare(_scene())
    results = list(progressive(prepared, replace(BASE, mosaic=True), CpuBackend()))
    assert results[0].samples == 0 and results[0].image.shape == (24, 40, 3)
    assert np.allclose(results[0].image[0, 0], results[0].image[3, 3])  # 4×4 blocks
    assert np.array_equal(results[-1].image, render(prepared, BASE, CpuBackend()).image)


def test_halton_and_random_converge_to_the_same_image() -> None:
    prepared, settings = prepare(_scene()), replace(BASE, samples=64, samples_per_pass=16)
    random = render(prepared, settings, CpuBackend()).image
    halton = render(prepared, replace(settings, sequence="halton"), CpuBackend()).image
    assert not np.array_equal(random, halton)
    assert abs(float(random.mean()) - float(halton.mean())) < 0.02


def test_per_lobe_limits_and_ao_direct_light() -> None:
    prepared = prepare(_scene())
    full = render(prepared, BASE, CpuBackend()).image
    no_diffuse = render(prepared, replace(BASE, diffuse_bounces=0), CpuBackend()).image
    assert no_diffuse.mean() < full.mean()  # no indirect light between the sphere and the box
    ao = replace(BASE, integrator="ao")
    plain, lit = (render(prepared, replace(ao, ao_direct=on), CpuBackend()).image for on in (False, True))
    assert lit.mean() > plain.mean()
