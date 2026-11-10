"""Render Settings overrides survive rebuilds and stay per tab (docs/14 §3)."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest
from PySide6.QtWidgets import QSpinBox
from pytestqt.qtbot import QtBot

from structura.render.aovs import Aovs
from structura.render.api import RenderProgress
from structura.render.post import PostSettings
from structura.render.settings import RenderSettings
from structura.services.render import RenderUpdate
from structura.ui.app_window import MainWindow
from structura.ui.panels.render_settings import RenderSettingsPanel
from structura.ui.render_view.controls import LOOK_SCRIPT


def _spin(panel: RenderSettingsPanel, key: str) -> QSpinBox:
    widget = panel.form.widgets[key]
    assert isinstance(widget, QSpinBox)
    return widget


def test_user_edits_survive_rebuilds_and_only_they_override(qtbot: QtBot) -> None:
    panel = RenderSettingsPanel()
    qtbot.addWidget(panel)
    script = RenderSettings(max_bounces=5)
    panel.show_settings(script)
    _spin(panel, "max_bounces").setValue(12)  # the user's edit
    panel.show_settings(replace(script, max_bounces=7, samples=64))  # the script changed and rebuilt
    assert _spin(panel, "max_bounces").value() == 12
    applied = panel.apply(replace(script, max_bounces=7, samples=64))
    assert applied.max_bounces == 12 and applied.samples == 64  # untouched fields follow the script
    panel.reset.click()
    assert panel.overrides == {} and _spin(panel, "max_bounces").value() == 7


def test_setting_a_value_back_to_the_script_drops_the_override(qtbot: QtBot) -> None:
    panel = RenderSettingsPanel()
    qtbot.addWidget(panel)
    panel.show_settings(RenderSettings(max_bounces=5))
    _spin(panel, "max_bounces").setValue(9)
    _spin(panel, "max_bounces").setValue(5)
    assert panel.overrides == {} and not panel.reset.isEnabled()


def test_overrides_are_kept_per_tab(window: MainWindow) -> None:
    first = window.docs.new_script()
    _spin(window.render_settings, "max_bounces").setValue(13)
    assert first.render_overrides == {"max_bounces": 13}
    window.docs.new_script()
    assert window.render_settings.overrides == {}
    window.tabs.setCurrentWidget(first)
    assert window.render_settings.overrides == {"max_bounces": 13}


def test_render_view_exposure_applies_without_re_rendering(window: MainWindow) -> None:
    view = window.render_view
    update = RenderUpdate(RenderProgress(np.full((8, 8, 3), 0.18, np.float32), 4, 0.1), "cpu", 4)
    view._on_update("render-view", update)
    assert view.view.image is not None
    before = view.view.image.pixelColor(4, 4).red()
    view.exposure.setValue(2.0)  # two stops brighter, from the same render
    assert view.view.image.pixelColor(4, 4).red() > before


def test_render_view_look_applies_live_and_follows_the_script(window: MainWindow) -> None:
    view = window.render_view
    update = RenderUpdate(RenderProgress(np.full((16, 16, 3), 0.18, np.float32), 4, 0.1), "cpu", 4)
    view._on_update("render-view", update)
    assert view.view.image is not None
    before = view.view.image.pixelColor(0, 0).red()
    view.controls.look.setCurrentText("Cinematic")  # a vignette darkens the corner, without re-rendering
    assert view.view.image.pixelColor(0, 0).red() < before
    assert view.display().post.vignette > 0
    script = RenderSettings(post=PostSettings(bloom=0.2))
    view.controls.show_script(script, ())
    assert view.controls.look.currentText() == LOOK_SCRIPT and view.display().post.bloom == 0.2
    view.controls.show_script(RenderSettings(), ())
    assert view.controls.look.findText(LOOK_SCRIPT) < 0


def test_a_large_image_is_tone_mapped_off_the_gui_thread(qtbot: QtBot, window: MainWindow) -> None:
    from structura.ui.render_view.render_view import LARGE  # noqa: PLC0415

    view = window.render_view
    side = int(LARGE**0.5) + 8
    update = RenderUpdate(RenderProgress(np.full((side, side, 3), 0.18, np.float32), 4, 0.1), "cpu", 4)
    view._on_update("render-view", update)  # no display made by a render job: a compute-lane job makes it
    qtbot.waitUntil(lambda: view.view.image is not None, timeout=30000)
    first = view.view.image
    assert first is not None
    view.exposure.setValue(2.0)  # large: a compute-lane job makes the new picture; the old one stays meanwhile
    assert view.view.image is first
    qtbot.waitUntil(lambda: view.view.image is not first, timeout=30000)
    assert view.last is not None and view.last.display_for == view.display()
    assert view.view.image.pixelColor(4, 4).red() > first.pixelColor(4, 4).red()


def test_a_failed_re_tone_map_keeps_the_picture_and_says_why(
    qtbot: QtBot, window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    from structura.render.output import Display  # noqa: PLC0415
    from structura.ui.render_view.render_view import LARGE  # noqa: PLC0415

    view = window.render_view
    side = int(LARGE**0.5) + 8
    update = RenderUpdate(RenderProgress(np.full((side, side, 3), 0.18, np.float32), 4, 0.1), "cpu", 4)
    view._on_update("render-view", update)
    qtbot.waitUntil(lambda: view.view.image is not None, timeout=30000)
    shown = view.view.image
    messages: list[str] = []
    view.status.connect(messages.append)

    def broken(self: Display, image: np.ndarray) -> np.ndarray:
        """Fails as tone mapping would without memory.

        Args:
            self: The display settings.
            image: The image to tone-map.

        Raises:
            RuntimeError: Always.
        """
        raise RuntimeError("no memory")

    monkeypatch.setattr(Display, "apply", broken)
    view.exposure.setValue(1.0)
    qtbot.waitUntil(lambda: bool(messages), timeout=30000)
    assert "no memory" in messages[-1] and view.view.image is shown


def test_render_view_shows_aov_channels_and_denoised_results(window: MainWindow) -> None:
    view = window.render_view
    shape = (8, 8)
    aovs = Aovs(np.full((*shape, 3), 0.5, np.float32), np.zeros((*shape, 3), np.float32),
                np.full(shape, 2.0, np.float32), np.ones(shape, np.float32), np.zeros(shape, np.int64),
                np.zeros(shape, np.int64))  # fmt: skip
    raw = np.full((*shape, 3), 0.18, np.float32)
    update = RenderUpdate(RenderProgress(raw, 4, 0.1, aovs), "cpu", 4, denoised=raw * 4, denoiser="atrous")
    view._on_update("render-view", update)
    assert view.shown_image() is update.denoised and "denoised (atrous)" in view.controls.info.text()
    view.controls.denoise.setCurrentText("off")
    assert view.shown_image() is raw
    view.controls.channel.setCurrentText("albedo")
    assert view.view.image is not None and view.view.image.pixelColor(4, 4).red() == 188  # sRGB(0.5)


def test_region_renders_paste_into_the_last_image_and_ab_snapshots(window: MainWindow) -> None:
    from structura.ui.render_view.regions import eta, merged  # noqa: PLC0415

    view = window.render_view
    base = RenderUpdate(RenderProgress(np.full((4, 4, 3), 0.2, np.float32), 8, 1.0), "cpu", 8)
    sample_map = np.zeros((4, 4), np.int32)
    sample_map[1:3, 1:3] = 8
    region = RenderUpdate(RenderProgress(np.full((4, 4, 3), 0.9, np.float32), 8, 1.0, sample_map=sample_map), "cpu", 8)
    image = merged(base, region).progress.image
    assert image[0, 0, 0] == np.float32(0.2) and image[1, 1, 0] == np.float32(0.9)
    assert eta(RenderUpdate(RenderProgress(image, 4, 2.0), "cpu", 8)) == " · 2 s left"
    view._on_update("render-view", base)
    view.toggle_snapshot()
    assert view.view.snapshot is not None
    view.inspect(1, 2)
    assert view.controls.pixel.text() == "1 2: 0.2 0.2 0.2"


def test_render_presets_set_samples_size_and_noise_threshold(window: MainWindow) -> None:
    controls = window.render_view.controls
    controls.preset.setCurrentText("Print 4K")
    assert controls.samples.value() == 2048 and controls.image_size((800, 600)) == (3840, 2880)
    assert controls.settings(64, 48).noise_threshold == 0.003
    controls.preset.setCurrentText("Draft")
    assert controls.image_size((600, 800)) == (720, 960)  # the long edge follows the viewport's orientation
    controls.samples.setValue(77)
    assert controls.preset.currentText() == "Custom" and controls.settings(64, 48).noise_threshold == 0.0
    assert controls.image_size((2000, 1000)) == (1280, 640)  # Custom: the viewport, capped


def test_tiled_renders_mark_the_next_bucket_and_count_buckets(window: MainWindow) -> None:
    view = window.render_view
    image = np.full((16, 16, 3), 0.2, np.float32)
    progress = RenderProgress(image, 8, 2.0, tile=(8, 0, 16, 8), completed=0.5)
    view._on_update("render-view", RenderUpdate(progress, "cpu", 8))
    assert view.view.bucket == (8, 0, 16, 8) and view.controls.progress.value() == 50
    assert "50% of the buckets" in view.controls.info.text() and "2 s left" in view.controls.info.text()
    view.view.grab()  # paints the corner marks
    view._on_update("render-view", RenderUpdate(replace(progress, tile=None, completed=1.0), "cpu", 8))
    assert view.view.bucket is None
