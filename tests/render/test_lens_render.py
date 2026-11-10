"""The lens in the precision engine (PLAN Q5): shift matches the viewport's projection, anamorphic and
biased bokeh, fisheye mappings, the tilted focus plane, and legacy depth of field on any camera."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from structura.compute.cpu import CpuBackend
from structura.core.build.api import build_scene
from structura.core.lang.api import compile_script
from structura.core.scene.camera import Camera
from structura.core.scene.lens import Lens
from structura.preview.camera import camera_matrices
from structura.render.api import prepare, prepare_with_frame, render, script_settings
from structura.render.settings import RenderSettings

W, H = 64, 48


def _alpha(text: str, camera: Camera) -> np.ndarray:
    scene = build_scene(compile_script(text).program).scene
    settings = RenderSettings(width=W, height=H, samples=4, samples_per_pass=4, integrator="preview", aovs=True)
    prepared, frame = prepare_with_frame(scene, settings, camera=camera)
    aovs = render(prepared, settings, CpuBackend(), frame).aovs
    assert aovs is not None
    return aovs.alpha


def _centroid(alpha: np.ndarray) -> np.ndarray:
    ys, xs = np.mgrid[0:H, 0:W]
    return np.array([(xs * alpha).sum(), (ys * alpha).sum()]) / alpha.sum()


@pytest.mark.parametrize(
    "lens", [Lens(shift=(0.1, 0.2)), Lens(projection="orthographic", ortho_height=6, shift=(0, -0.2))]
)
def test_lens_shift_renders_where_the_viewport_shows_it(lens: Lens) -> None:
    camera = Camera((0.0, 0.0, 10.0), (0.0, 0.0, 0.0), fov_y_deg=30.0, lens=lens)
    alpha = _alpha("{ x -0.5 y -0.5 z -0.5 } sphere\n", camera)  # a unit sphere around the origin
    m = camera_matrices(camera, W / H, np.full(3, -1.0), np.full(3, 1.0))
    clip = m.proj @ m.view @ np.array([0.0, 0.0, 0.0, 1.0])
    expected = np.array([(clip[0] / clip[3] + 1) / 2 * W, (1 - clip[1] / clip[3]) / 2 * H]) - 0.5
    assert np.allclose(_centroid(alpha), expected, atol=0.6)
    unshifted = _alpha("{ x -0.5 y -0.5 z -0.5 } sphere\n", replace(camera, lens=replace(lens, shift=(0.0, 0.0))))
    assert not np.allclose(_centroid(alpha), _centroid(unshifted), atol=2.0)


def _bokeh(camera_keys: str) -> np.ndarray:
    script = ("#version 2\nenvironment { type color color #000000 }\nmaterial lamp { emission #fff 40 }\n"
              f"camera {{ position [0 0 8] target [0 0 0] fov 20 aperture 0.5 focus 3 {camera_keys} }}\n"
              "{ x -0.05 y -0.05 z -0.05 s 0.1 } sphere::lamp\n")  # fmt: skip
    scene = build_scene(compile_script(script).program).scene
    settings = replace(script_settings(scene), width=48, height=48, samples=256, samples_per_pass=64, integrator="path")
    return render(prepare(scene), settings, CpuBackend()).image.mean(axis=2)


def _extent(image: np.ndarray) -> tuple[int, int]:
    lit = image > image.max() * 0.05
    return int(lit.any(axis=0).sum()), int(lit.any(axis=1).sum())


def test_anamorphic_bokeh_is_wider_than_tall() -> None:
    width, height = _extent(_bokeh("anamorphic 1.8"))
    assert width > 1.25 * height  # the lamp's own size adds to both
    round_w, round_h = _extent(_bokeh(""))
    assert abs(round_w - round_h) <= 2


def test_bokeh_bias_moves_light_to_the_rim() -> None:
    def rim_ratio(image: np.ndarray) -> float:
        """How much brighter a bokeh disc's rim is than its centre."""
        ys, xs = np.mgrid[0:48, 0:48]
        r = np.hypot(xs - 23.5, ys - 23.5)
        radius = r[image > image.max() * 0.05].max()
        return float(image[r > 0.7 * radius].mean() / max(image[r < 0.4 * radius].mean(), 1e-9))

    assert rim_ratio(_bokeh("bokeh_bias 1")) > 1.5 * rim_ratio(_bokeh("bokeh_bias -1"))


def test_fisheye_mappings_differ_and_tilt_renders() -> None:
    text = "{ x -10 y -1 z -10 s 20 0.2 20 } box\n{ y 1 } sphere\n"
    base = Camera((0.0, 3.0, 6.0), (0.0, 0.0, 0.0), lens=Lens(projection="fisheye", fisheye_fov_deg=170.0))
    images = [_alpha(text, replace(base, lens=replace(base.lens, fisheye_mapping=m)))
              for m in ("equidistant", "equisolid", "stereographic")]  # fmt: skip
    assert all(img.mean() > 0.02 for img in images)
    assert not np.allclose(images[0], images[2], atol=0.1)
    tilted = Camera((0.0, 3.0, 6.0), (0.0, 0.0, 0.0), lens=Lens(aperture_radius=0.3, tilt=(20.0, 0.0)))
    assert np.isfinite(_alpha(text, tilted)).all()


def test_legacy_depth_of_field_applies_to_the_viewport_camera() -> None:
    scene = build_scene(compile_script("set raytracer::dof [0.2,0.1]\nbox\n").program).scene
    settings = script_settings(scene)
    _, frame = prepare_with_frame(scene, settings, camera=Camera((0.0, 0.0, 10.0), (0.0, 0.0, 0.0)))
    assert frame.camera.aperture_radius > 0 and frame.camera.lens.focus_mode == "manual"
