"""Colour-by modes (docs/08 §5)."""

from __future__ import annotations

import numpy as np

from structura.core.build.api import build_scene
from structura.core.lang.api import compile_script
from structura.core.scene.color_by import MODES, categorical, cividis, recolored

SCENE = build_scene(compile_script("R\nrule R md 4 { { x 1 } R box }\n{ y 2 } sphere::shiny\n").program).scene


def test_authored_keeps_the_scene() -> None:
    assert recolored(SCENE, "authored") is SCENE


def test_every_mode_keeps_alpha_and_stays_in_gamut() -> None:
    for mode in MODES[1:]:
        rgba = recolored(SCENE, mode).rgba
        assert rgba.shape == SCENE.rgba.shape and np.array_equal(rgba[:, 3], SCENE.rgba[:, 3])
        assert rgba.min() >= 0.0 and rgba.max() <= 1.0


def test_generations_follow_cividis_and_categories_differ() -> None:
    generation = recolored(SCENE, "generation").rgba[:, :3]
    order = np.argsort(SCENE.generation)
    luminance = generation[order] @ [0.2126, 0.7152, 0.0722]
    assert np.all(np.diff(luminance) >= -1e-6)  # deeper generations are lighter (cividis is monotonic)
    kinds = recolored(SCENE, "kind").rgba[:, :3]
    box, sphere = SCENE.kind == 0, SCENE.kind == 1
    assert not np.allclose(kinds[box][0], kinds[sphere][0]) and np.allclose(kinds[box], kinds[box][0])
    assert np.allclose(cividis(np.array([0.0]))[0], [0.0, 0.135, 0.304])
    assert len({tuple(c) for c in categorical(np.arange(20)).round(3)}) == 20  # distinct beyond the base 8


def test_view_filter_xray_and_isolation_keep_rows() -> None:
    from structura.core.scene.view_filter import XRAY_ALPHA, ViewFilter  # noqa: PLC0415

    shown = ViewFilter(xray=True, isolate=np.array([0, 1])).apply(SCENE)
    assert len(shown) == len(SCENE) and np.all(shown.rgba[:, 3] <= XRAY_ALPHA)
    assert np.any(shown.xform[0, :, :3]) and not np.any(shown.xform[-1, :, :3])  # hidden: a point
    assert np.array_equal(shown.xform[:, :, 3], SCENE.xform[:, :, 3])  # positions (provenance) unchanged
    assert ViewFilter().apply(SCENE) is SCENE
