"""'set raytracer::…' → render settings (docs/05 §6.3, docs/10 §6.1)."""

from __future__ import annotations

import numpy as np
import pytest

from structura.core.scene.camera import LegacyView
from structura.render.legacy import default_light, legacy_lens, with_legacy
from structura.render.settings import RenderSettings


def test_keys_map_to_settings_and_bad_values_are_ignored() -> None:
    keys = [
        ("samples", "6"),
        ("ambient-occlusion-samples", "2"),
        ("max-depth", "3"),
        ("shadows", "false"),
        ("light", "1,2,3"),
        ("size", "800x0"),
        ("samples", "lots"),
        ("voxel-steps", "30"),
    ]
    s = with_legacy(RenderSettings(), keys)
    assert (s.samples, s.ao_samples, s.max_bounces, s.shadows) == (36, 4, 3, False)
    assert s.light_position == (1.0, 2.0, 3.0)
    assert (s.width, s.height) == (800, 600)


def test_legacy_dof_becomes_a_thin_lens_in_world_units() -> None:
    view = LegacyView(scale=0.5, fov_y_deg=22.0)
    aperture, focus = legacy_lens(view, (0.2, 0.01))
    assert focus == pytest.approx((5 + 55 * 0.2) / 0.5)
    assert aperture == pytest.approx(0.01 * 2 * 5 * np.tan(np.radians(11)) / 0.5)


def test_default_light_sits_up_and_left_on_the_near_plane() -> None:
    view = LegacyView()
    camera = view.camera()
    light = np.array(default_light(camera, 4 / 3, 1 / view.scale))
    forward, right, up = camera.basis
    rel = light - np.array(camera.eye)
    assert rel @ right < 0 and rel @ up > 0
    assert rel @ forward == pytest.approx(5 / view.scale)
