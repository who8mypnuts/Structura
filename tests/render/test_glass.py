"""Glass and transparency in the precision engine (PLAN Q1): Beer–Lambert absorption, thin walls, see-through
instances in every integrator, and the special material models."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from structura.compute.cpu import CpuBackend
from structura.core.build.api import build_scene
from structura.core.color import linear_of
from structura.core.lang.api import compile_script
from structura.render.api import prepare_with_frame, render, script_settings

WHITE_ROOM = "environment { type color color #fff }\n"


def _render(text: str, samples: int = 16, **settings: object) -> np.ndarray:
    scene = build_scene(compile_script(text).program).scene
    st = replace(script_settings(scene), width=48, height=36, samples=samples, samples_per_pass=samples, frame=True,
                 **settings)  # fmt: skip
    prepared, frame = prepare_with_frame(scene, st)
    return render(prepared, st, CpuBackend(), frame).image


def _glass(extra: str) -> np.ndarray:
    return _render(f"#version 2\nmaterial g {{ preset glass ior 1.0001 {extra} }}\n{WHITE_ROOM}{{ s 2 }} box::g\n")


@pytest.mark.parametrize("distance", [1.0, 4.0])
def test_absorption_follows_beer_lambert(distance: float) -> None:
    """Straight through a 2-unit box (index ≈ 1: no bending, no reflection) the white room dims to
    colour^(2 / distance), per channel, in linear light."""
    centre = _glass(f"attenuation_color #c08040 attenuation_distance {distance:g}")[18, 24]
    expected = np.asarray(linear_of("#c08040", (1.0, 1.0, 1.0))) ** (2.0 / distance)
    assert np.allclose(centre, expected, atol=0.02)


def test_clear_and_thin_walled_glass_absorb_nothing() -> None:
    assert np.allclose(_glass("")[18, 24], 1.0, atol=0.01)
    thin = _glass("attenuation_color #f00 attenuation_distance 0.1 thin_walled true")  # thin walls never absorb
    assert np.allclose(thin[18, 24], 1.0, atol=0.01)


def test_see_through_instances_in_every_integrator() -> None:
    opaque, clear = "{ s 2 } box\n", "{ a 0.25 s 2 } box\n"
    for integrator in ("preview", "ao", "path"):
        solid = _render(opaque, 64, integrator=integrator)[18, 24].sum()
        seen = _render(clear, 64, integrator=integrator)[18, 24].sum()
        assert 0.1 * solid < seen < 0.45 * solid, integrator  # about a quarter of the rays stop at the box


def test_special_material_models() -> None:
    def centre(model: str, integrator: str = "path") -> np.ndarray:
        """The mean colour of the image's centre for one material model."""
        text = f"#version 2\nmaterial m {{ model {model} }}\n{{ s 2 color #fff }} box::m\n"
        return _render(text, 4, integrator=integrator)[18, 24]

    assert np.allclose(centre("debug_normal"), (0.5, 0.5, 1.0), atol=0.02)  # facing the camera (+z)
    assert np.allclose(centre("debug_normal", "preview"), centre("debug_normal"), atol=0.02)
    assert np.allclose(centre("wireframe"), 0.12, atol=0.02)  # the middle of a face: the dark fill
    assert centre("debug_gray").min() > 0.85  # facing the camera: bright grey
    assert 0.0 < centre("ao").mean() <= 1.0


def test_the_kernels_material_models_match_the_enum() -> None:
    from structura.core.scene.material import MaterialModel  # noqa: PLC0415
    from structura.render.kernels import layout  # noqa: PLC0415

    names = {m: f"MODEL_{'CATCHER' if m.name == 'SHADOW_CATCHER' else m.name}" for m in MaterialModel}
    assert {m: getattr(layout, name) for m, name in names.items()} == {m: int(m) for m in MaterialModel}
