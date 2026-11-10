"""Every lighting rig renders a lit, unclipped image (PLAN F3)."""

from __future__ import annotations

import numpy as np
import pytest

from structura import api
from structura.core.scene.light_rigs import apply_rig, rigs
from structura.render.api import script_settings

SCRIPT = "#version 2\n{ s 2 } sphere\n3 * { x 1.2 ry 30 } box\n"


@pytest.mark.parametrize("name", list(rigs()))
def test_each_rig_lights_the_structure(name: str) -> None:
    text = apply_rig(SCRIPT, rigs()[name], np.array([-1.0, -1.0, -1.0]), np.array([3.4, 1.0, 1.2]))
    scene = api.build(text)
    result = api.render(scene, device="cpu", width=48, height=36, samples=8, frame=True)
    image = result.image
    assert np.isfinite(image).all()
    assert image[12:24, 12:36].mean() > 0.01, "the structure is lit"
    shown = script_settings(scene).display.apply(image)
    assert (shown >= 254).mean() < 0.05, "and not blown out"


@pytest.mark.parametrize("integrator", ["preview", "ao"])
def test_preview_and_ao_show_the_declared_sky(integrator: str) -> None:
    """Camera rays that miss see the environment a v2 script declares (like the path tracer), else the
    background colour."""
    sky = api.build("#version 2\nenvironment { type color  color #3366ff }\nbox\n")
    plain = api.build("box\n")
    corner = [api.render(s, device="cpu", width=24, height=16, samples=1, integrator=integrator, frame=True)
              .image[0, 0] for s in (sky, plain)]  # fmt: skip
    assert corner[0][2] > corner[0][0] * 3  # blue sky
    np.testing.assert_allclose(corner[1], 0.0, atol=1e-6)  # the default black background
