"""AOV previews for the Render view's channel selector."""

from __future__ import annotations

import numpy as np

from structura.render.aov_display import CHANNELS, PREVIEWS, channel_preview, depth_preview, heat_preview, id_preview


def test_every_channel_but_beauty_has_a_preview() -> None:
    assert set(CHANNELS) == {"beauty", "samples", *PREVIEWS}
    assert channel_preview("beauty", None, None) is None and channel_preview("albedo", None, None) is None


def test_the_sample_heat_map_runs_from_black_to_white() -> None:
    shown = heat_preview(np.array([[0, 32, 64]]))
    assert np.all(shown[0, 0] == 0.0) and np.all(shown[0, 2] == 1.0) and 0 < shown[0, 1].mean() < 1
    assert channel_preview("samples", None, np.array([[0, 64]])) is not None


def test_depth_is_bright_near_and_black_on_the_background() -> None:
    shown = depth_preview(np.array([[1.0, 3.0, np.inf]], np.float32))
    assert shown[0, 0, 0] == 1.0 and 0.1 < shown[0, 1, 0] < 0.2 and shown[0, 2, 0] == 0.0


def test_ids_get_distinct_colours_and_the_background_is_black() -> None:
    shown = id_preview(np.array([[-1, 0, 1, 2]]))
    assert np.all(shown[0, 0] == 0.0)
    colours = {tuple(np.round(c, 3)) for c in shown[0, 1:]}
    assert len(colours) == 3 and all(0.0 <= v <= 1.0 for c in colours for v in c)
