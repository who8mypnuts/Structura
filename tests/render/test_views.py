"""View transforms (docs/09 §7)."""

from __future__ import annotations

import numpy as np
import pytest

from structura.render.output import to_display
from structura.render.settings import VIEWS, RenderSettings
from structura.render.views import VIEW_TRANSFORMS


@pytest.mark.parametrize("name", sorted(VIEW_TRANSFORMS))
def test_transforms_are_monotonic_bounded_and_black_stays_black(name: str) -> None:
    ramp = np.geomspace(1e-4, 1e3, 400)[:, None] * np.ones(3)
    out = VIEW_TRANSFORMS[name](ramp)
    assert np.all(out >= 0) and np.all(out <= 1) and np.all(np.diff(out[:, 1]) >= -1e-9)
    assert VIEW_TRANSFORMS[name](np.zeros((1, 3))).max() < 0.02
    grey = float(VIEW_TRANSFORMS[name](np.full((1, 3), 0.18))[0, 1])
    assert 0.05 < grey < 0.4  # mid grey stays mid grey (display-linear)


def test_agx_desaturates_very_bright_colours_instead_of_clipping_hue() -> None:
    bright_red = np.array([[4.0, 0.2, 0.1]])

    def saturation(rgb: np.ndarray) -> float:
        return float((rgb.max() - rgb.min()) / rgb.max())

    clipped = VIEW_TRANSFORMS["standard"](bright_red)[0]  # [1, 0.2, 0.1]: as saturated as it gets
    agx = VIEW_TRANSFORMS["agx"](bright_red)[0]
    assert saturation(agx) < 0.85 * saturation(clipped)  # over-exposed colours move towards white, like film


def test_auto_picks_agx_except_for_the_classic_look() -> None:
    assert RenderSettings().view_transform == "agx"
    assert RenderSettings(integrator="classic").view_transform == "standard"
    assert set(VIEWS) - {"auto"} == set(VIEW_TRANSFORMS)
    assert to_display(np.full((2, 2, 3), 0.5, np.float32), 1.0, "agx").dtype == np.uint8
