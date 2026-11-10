"""Viewport colour modes and overlays (docs/08 §5, §8)."""

from __future__ import annotations

import numpy as np
from pytestqt.qtbot import QtBot

from structura.core.scene.camera import Camera
from structura.ui.app_window import MainWindow
from structura.ui.viewport.overlay import project


def test_projection_puts_the_target_in_the_middle() -> None:
    camera = Camera((0.0, 0.0, 10.0), (0.0, 0.0, 0.0))
    lo, hi = np.full(3, -1.0), np.full(3, 1.0)
    px = project(camera, (200, 100), lo, hi, np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 20.0]]))
    assert np.allclose(px[0], [100, 50]) and np.isnan(px[1]).all()  # behind the camera


def test_colour_by_recolours_the_viewport_only(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("{ color #f00 } box\n{ x 2 color #f00 } sphere\n")
    qtbot.waitUntil(lambda: window.viewport.scene is not None, timeout=30000)
    window.registry.trigger("view.color_kind")
    qtbot.waitUntil(lambda: window.viewport.scene is not tab.outcome.scene, timeout=30000)
    shown = window.viewport.scene
    assert not np.allclose(shown.rgba[0], shown.rgba[1])  # box and sphere differ now
    assert np.allclose(tab.outcome.scene.rgba[:, :3], [1.0, 0.0, 0.0])  # renders and exports keep red
    assert window.registry.action("view.color_kind").isChecked()
    window.registry.trigger("view.color_authored")
    qtbot.waitUntil(lambda: window.viewport.scene is tab.outcome.scene, timeout=30000)


def test_overlay_commands_toggle_and_persist(window: MainWindow) -> None:
    overlay = window.viewport.overlay
    assert overlay.options.axes and not overlay.options.bounds and not window.viewport.options.grid
    window.registry.trigger("view.overlay_bounds")
    window.registry.trigger("view.overlay_grid")
    assert overlay.options.bounds and window.viewport.options.grid
    assert window.settings.value("viewport/bounds", False) is True or window.settings.value("viewport/bounds") == "true"
    assert overlay.geometry() == window.viewport.rect()


def test_compute_preview_picks_on_the_cpu_and_alt_click_focuses(qtbot: QtBot, window: MainWindow) -> None:
    from PySide6.QtCore import QPoint  # noqa: PLC0415

    tab = window.docs.new_script()
    tab.editor.setPlainText("{ s 4 } box\n")
    qtbot.waitUntil(lambda: window.viewport.scene is not None, timeout=30000)
    window.viewport.frame_all()
    centre = QPoint(window.viewport.width() // 2, window.viewport.height() // 2)
    picked: list[object] = []
    window.viewport.picked.connect(picked.append)
    window.viewport._clicked(centre, False)
    qtbot.waitUntil(lambda: bool(picked), timeout=30000)
    assert picked[0] == 0
    window.viewport._clicked(centre, True)
    qtbot.waitUntil(lambda: window.viewport.camera().lens.focus_distance is not None, timeout=30000)
    camera = window.viewport.camera()
    assert camera.lens.focus_mode == "manual" and 0 < camera.focus < camera.distance
    window.viewport.select(0)
    window.registry.trigger("view.frame_selection")


def test_xray_and_isolate_change_the_viewport_only(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("3 * { x 1.5 } box\n{ y 2 } sphere\n")
    qtbot.waitUntil(lambda: window.viewport.scene is not None, timeout=30000)
    window.registry.trigger("view.xray")
    qtbot.waitUntil(lambda: window.viewport.scene.rgba[0, 3] < 0.5, timeout=30000)
    window.on_picked(0)
    window.inspector.buttons["rule"].click()
    window.inspector.isolate_rows.emit(window.inspector.selected)
    qtbot.waitUntil(lambda: not window.viewport.scene.xform[3, :, :3].any(), timeout=30000)  # the sphere hidden
    assert tab.outcome.scene.rgba[0, 3] == 1.0 and tab.outcome.scene.xform[3, :, :3].any()
    window.registry.trigger("view.show_all")
    qtbot.waitUntil(lambda: window.viewport.scene.xform[3, :, :3].any(), timeout=30000)  # noqa: PLW0108 - re-read


def test_rendered_view_path_traces_the_viewport(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("set raytracer::samples 4\n{ color #f80 } sphere\n")
    qtbot.waitUntil(lambda: window.viewport.scene is not None, timeout=30000)
    window.registry.trigger("view.rendered")
    compute = window.viewport.compute
    assert window.viewport.rendered and compute._settings(False).integrator == "path"
    assert compute.badge_text().endswith("rendered") and window.registry.action("view.rendered").isChecked()
    window.registry.trigger("view.rendered")
    assert not window.viewport.rendered and compute._settings(False).integrator == "preview"


def test_the_compute_preview_outlines_the_selection(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("{ x 2 s 2 } box\n")
    qtbot.waitUntil(lambda: window.viewport.scene is not None, timeout=30000)
    window.on_picked(0)
    corners = window.viewport.overlay.selected
    xform = tab.outcome.scene.xform[0]
    assert corners is not None and corners.shape == (8, 3)
    assert np.allclose(corners[0], xform[:, 3]) and np.allclose(corners[7], xform[:, 3] + xform[:, :3].sum(axis=1))
    window.on_picked(None)
    assert window.viewport.overlay.selected is None
