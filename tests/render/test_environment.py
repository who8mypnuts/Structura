"""Environment maps (docs/10 §4): HDRI importance sampling is unbiased, the Preetham sky is plausible."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from structura.compute.cpu import CpuBackend
from structura.core.build.api import build_scene
from structura.core.lang.api import compile_script
from structura.core.scene.material import Material
from structura.render.api import prepare, render
from structura.render.environment import directions, preetham_sky, sampling_tables
from structura.render.hdr_io import read_hdr, write_hdr
from structura.render.settings import RenderSettings

WHITE_DIFFUSE = Material(base=(1.0, 1.0, 1.0), roughness=1.0, specular=0.0)


def _render(script: str, env_file: Path, **overrides: object) -> np.ndarray:
    scene = build_scene(compile_script(script).program).scene
    settings = RenderSettings(width=32, height=24, samples=48, samples_per_pass=48, integrator="path",
                              max_bounces=8, sun_irradiance=(0.0, 0.0, 0.0), env_type="hdri",
                              env_file=str(env_file), clamp=1e6, **overrides)  # type: ignore[arg-type]  # fmt: skip
    return render(prepare(scene, declared={"": WHITE_DIFFUSE}), settings, CpuBackend()).image


def test_white_furnace_with_an_environment_map(tmp_path: Path) -> None:
    write_hdr(tmp_path / "white.hdr", np.ones((64, 128, 3), np.float32))
    image = _render("set background #fff\nsphere\n{ x 1.2 s 0.8 } box", tmp_path / "white.hdr", frame=True,
                    backdrop_sky=True)  # fmt: skip
    assert float(image.mean()) == pytest.approx(1.0, abs=0.02)


def test_a_bright_cap_lights_a_floor_as_predicted(tmp_path: Path) -> None:
    height, rows, radiance = 128, 8, 10.0
    env = np.zeros((height, 256, 3), np.float32)
    env[:rows] = radiance  # a cap around the zenith
    write_hdr(tmp_path / "cap.hdr", env)
    camera = "camera { position [0.5 6 0.51] target [0.5 0.5 0.5] fov 30 }"
    floor = f"#version 2\n{camera}\n{{ s 20 0.1 20 }} box\n"  # 's' scales about the unit-cube centre
    image = _render(floor, tmp_path / "cap.hdr")
    cap = rows / height * math.pi
    assert float(image.mean()) == pytest.approx(radiance * math.sin(cap) ** 2, rel=0.05)


def test_hdr_round_trip_and_sampling_tables(tmp_path: Path) -> None:
    rgb = np.random.default_rng(1).random((16, 32, 3)).astype(np.float32) * 4
    write_hdr(tmp_path / "a.hdr", rgb)
    assert np.allclose(read_hdr(tmp_path / "a.hdr"), rgb, rtol=0.0, atol=0.07)  # RGBE: 1/256 of the peak mantissa
    cdf = sampling_tables(rgb)
    assert cdf.shape == (17 + 16 * 33,) and cdf[16] == pytest.approx(1.0) and np.all(np.diff(cdf[:17]) >= 0)


def test_preetham_sky_is_blue_overhead_and_red_at_sunset() -> None:
    noon = preetham_sky((0.3, 0.9, 0.3), 3.0, size=(64, 32))
    sunset = preetham_sky((0.0, 0.03, 1.0), 3.0, size=(64, 32))
    zenith = noon[0].mean(axis=0)
    assert zenith[2] > zenith[0]  # blue sky
    towards_sun = sunset[15, 32 - 1]  # near the horizon, around the sun's azimuth
    assert towards_sun[0] > towards_sun[2]  # red-orange sunset glow
    assert directions(64, 32).shape == (32, 64, 3)
