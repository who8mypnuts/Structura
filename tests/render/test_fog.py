"""Fog (docs/10 §2.3): rays fade towards the fog colour with optical depth."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from structura.compute.cpu import CpuBackend
from structura.core.build.api import build_scene
from structura.core.color import srgb_to_linear
from structura.core.lang.api import compile_script
from structura.render.api import prepare_with_frame, progressive
from structura.render.settings import RenderSettings

BASE = RenderSettings(width=32, height=24, samples=8, samples_per_pass=8, integrator="path", frame=True)
FOG = (0.6, 0.7, 0.8)


def _render(text: str, settings: RenderSettings) -> np.ndarray:
    scene = build_scene(compile_script(text).program).scene
    prepared, frame = prepare_with_frame(scene, settings)
    *_, last = progressive(prepared, settings, CpuBackend(), frame)
    return last.image


def test_even_fog_hides_the_background_completely() -> None:
    image = _render("set background #000\nbox\n", replace(BASE, fog_density=0.05, fog_color=FOG))
    expected = srgb_to_linear(np.asarray(FOG, np.float32))
    assert np.allclose(image[0, 0], expected, atol=1e-4)  # an escaped ray crosses infinite fog


def test_far_objects_are_foggier_and_height_fog_thins_out_upwards() -> None:
    text = ("#version 2\ncamera { position [0.5 0.5 8] target [0.5 0.5 0] fov 40 }\nset background #000\n"
            "{ x -1.5 color #f00 } box\n{ x 8 z -30 s 4 color #f00 } box\n")  # fmt: skip
    settings = replace(BASE, frame=False, width=64, height=48)
    fogged = _render(text, replace(settings, fog_density=0.02, fog_color=FOG))
    clear = _render(text, settings)
    red = np.nonzero(clear[24, :, 0] > 0.05)[0]
    near, far = red[2], red[-3]  # inside each box, away from anti-aliased edges
    assert far - near > 20  # both boxes are in view, the near one on the left
    added = fogged[24, :, 2] - clear[24, :, 2]  # blue comes only from the fog
    assert added[far] > added[near] + 0.1  # the far box is much foggier than the near one
    high = _render("set background #000\nbox\n", replace(BASE, fog_density=0.05, fog_falloff=0.5, fog_color=FOG))
    assert high[0, 16, 2] < high[-1, 16, 2]  # rays towards the sky cross little fog
