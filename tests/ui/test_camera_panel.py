"""The Camera panel (docs/14 §3): numbers, standard views, saved views, Copy to Script."""

from __future__ import annotations

import numpy as np
from pytestqt.qtbot import QtBot

from structura.core.scene.camera import Camera
from structura.ui.app_window import MainWindow


def test_camera_panel_follows_and_drives_the_viewport(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("3 * { x 1.5 } box\n")
    qtbot.waitUntil(lambda: window.viewport.bounds() is not None, timeout=30000)
    panel, viewport = window.camera_panel, window.viewport
    window.cameras.standard_view("top")
    camera = viewport.camera()
    assert np.allclose(panel.eye.value(), camera.eye, atol=1e-3)  # the panel follows
    assert camera.eye[1] > camera.target[1] and abs(camera.eye[0] - camera.target[0]) < 1e-6
    panel.fov.setValue(40.0)  # an edit moves the viewport
    assert abs(viewport.camera().fov_y_deg - 40.0) < 1e-6
    window.cameras.add_view(tab, "overhead", viewport.camera())
    window.cameras.standard_view("front")
    assert panel.list.count() == 1
    panel._choose(panel.list.item(0))
    assert np.allclose(viewport.camera().eye, camera.eye, atol=1e-3)
    window.cameras.copy_to_script()
    assert tab.text().startswith("// camera") and "set perspective-angle 40" in tab.text()
    tab.editor.undo()
    assert tab.text() == "3 * { x 1.5 } box\n"


def test_inspector_shows_the_pick_and_selects_alike(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("3 * { x 1.5 } box\n{ y 2 color #f00 } sphere\n")
    qtbot.waitUntil(lambda: tab.outcome is not None and tab.analysis is not None, timeout=30000)
    inspector = window.inspector
    window.on_picked(3)  # the sphere
    assert inspector.labels["Object"].text() == "sphere #3" and "#ff0000" in inspector.labels["Colour"].text()
    assert inspector.labels["Source"].text() == "line 2"
    assert list(inspector.rows_like("kind")) == [3] and len(inspector.rows_like("generation")) >= 1
    window.on_picked(0)
    assert list(inspector.rows_like("rule")) == [0, 1, 2]  # the three boxes of the loop
    selected: list[object] = []
    inspector.select_rows.connect(selected.append)
    inspector.buttons["rule"].click()
    assert list(selected[0]) == [0, 1, 2] and "3 objects" in inspector.selection.text()  # type: ignore[call-overload]
    inspector.source_button.click()
    assert tab.editor.textCursor().position() == 0
    window.on_picked(None)
    assert not inspector.source_button.isEnabled()


def test_camera_moves_glide_unless_motion_is_reduced(qtbot: QtBot, window: MainWindow) -> None:
    from structura.core.scene.camera import Camera  # noqa: PLC0415
    from structura.ui.viewport.camera_motion import interpolate  # noqa: PLC0415

    a, b = Camera((0.0, 0.0, 10.0), (0.0, 0.0, 0.0)), Camera((10.0, 0.0, 0.0), (0.0, 0.0, 0.0), fov_y_deg=40.0)
    half = interpolate(a, b, 0.5)
    assert np.isclose(np.linalg.norm(half.eye), 10.0) and half.fov_y_deg == 31.0  # turns around the target
    window.settings.set_value("appearance/reduce_motion", False)
    window.viewport.set_camera(a)
    window.viewport.move_camera(b)
    assert np.allclose(window.viewport.camera().eye, a.eye)  # not there yet
    qtbot.waitUntil(lambda: np.allclose(window.viewport.camera().eye, b.eye, atol=1e-6), timeout=5000)


def test_history_snapshots_restore_text_seed_and_camera(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("3 * { x 1.5 } box\n")
    qtbot.waitUntil(lambda: tab.outcome is not None, timeout=30000)
    window.cameras.standard_view("top")
    window.registry.trigger("build.snapshot")
    assert len(tab.snapshots) == 1 and window.history.strip.count() == 1 and window.docks["History"].isVisible()
    kept = tab.snapshots[0]
    tab.editor.setPlainText("sphere\n")
    window.build_actions.next_seed()
    window.cameras.standard_view("front")
    window.history.restore_requested.emit(kept)
    assert tab.text() == "3 * { x 1.5 } box\n" and tab.seed == kept.seed
    assert np.allclose(window.viewport.camera().eye, kept.camera.eye, atol=1e-6)
    tab.editor.undo()
    assert tab.text() == "sphere\n"  # the restore was one undo step


def test_inspector_shows_the_ancestry_of_a_picked_object(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("R\nrule R md 3 { { x 1 } R box }\n")
    qtbot.waitUntil(lambda: tab.outcome is not None and tab.analysis is not None, timeout=30000)
    window.on_picked(len(tab.outcome.scene) - 1)
    window.inspector.ancestry_button.click()
    lines = window.inspector.ancestry
    qtbot.waitUntil(lambda: lines.count() > 2 and "line" in lines.item(1).text(), timeout=30000)
    assert lines.item(0).text() == "top level" and lines.item(lines.count() - 1).text().strip().startswith("box")
    lines.itemClicked.emit(lines.item(1))
    assert tab.editor.textCursor().position() == 0  # the top-level call 'R' on line 1


def test_lock_to_script_shows_the_script_camera_after_every_build(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("#version 2\ncamera { position [0 0 12] target [0 0 0] fov 30 }\nbox\n")
    qtbot.waitUntil(lambda: tab.outcome is not None, timeout=30000)
    assert np.allclose(window.viewport.camera().eye, (0, 0, 12), atol=1e-4)  # v2 camera blocks on first build
    window.viewport.move_camera(Camera((5.0, 5.0, 5.0), (0.0, 0.0, 0.0)))
    window.camera_panel.lock.setChecked(True)
    assert tab.camera_locked
    qtbot.waitUntil(lambda: np.allclose(window.viewport.camera().eye, (0, 0, 12), atol=1e-4), timeout=5000)
    window.viewport.move_camera(Camera((5.0, 5.0, 5.0), (0.0, 0.0, 0.0)))
    tab.editor.setPlainText("#version 2\ncamera { position [0 0 12] target [0 0 0] fov 30 }\nbox\nsphere\n")
    qtbot.waitUntil(lambda: np.allclose(window.viewport.camera().eye, (0, 0, 12), atol=1e-4), timeout=30000)
