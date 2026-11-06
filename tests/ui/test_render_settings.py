"""Render Settings overrides survive rebuilds and stay per tab (docs/14 §3)."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
from PySide6.QtWidgets import QSpinBox
from pytestqt.qtbot import QtBot

from structura.render.aovs import Aovs
from structura.render.api import RenderProgress
from structura.render.settings import RenderSettings
from structura.services.render import RenderUpdate
from structura.ui.app_window import MainWindow
from structura.ui.panels.render_settings import RenderSettingsPanel


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
