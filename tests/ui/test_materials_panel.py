"""The Materials panel (docs/14 §3)."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QMessageBox
from pytestqt.qtbot import QtBot

from structura.ui.app_window import MainWindow


def test_materials_panel_lists_tags_previews_and_writes_blocks(
    qtbot: QtBot, window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("box::shiny\n{ x 2 } sphere::gold\n")
    panel = window.materials
    qtbot.waitUntil(lambda: panel.list.count() == 2, timeout=30000)
    names = [panel.list.item(i).data(256) for i in range(panel.list.count())]
    assert names == ["gold", "shiny"]
    panel.list.setCurrentRow(0)
    assert panel.preset.currentText() == "gold" and panel.material().metallic == 1.0
    panel.form.set_values({"roughness": 0.6})
    qtbot.waitUntil(lambda: panel.swatch.pixmap() is not None and not panel.swatch.pixmap().isNull(), timeout=60000)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    panel.write.click()
    assert tab.text().startswith("#version 2") and "material gold {\n  preset gold\n  roughness 0.6\n}" in tab.text()


def test_lights_panel_adds_finds_and_removes_light_blocks(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("#version 2\n3 * { x 1.5 } box\n")
    qtbot.waitUntil(lambda: tab.outcome is not None and window.viewport.bounds() is not None, timeout=30000)
    window.light_actions.add("spot")
    window.light_actions.add("spot")
    assert "light spot1 {" in tab.text() and "light spot2 {" in tab.text()
    panel = window.lights
    qtbot.waitUntil(lambda: panel.list.count() == 2, timeout=30000)  # rebuilt with the lights
    window.light_actions.go_to("spot2")
    assert tab.editor.textCursor().position() == tab.text().index("light spot2")
    window.light_actions.remove("spot1")
    assert "spot1" not in tab.text() and "light spot2" in tab.text()
    scene = tab.outcome.scene
    assert scene.declarations is not None


def test_lights_panel_applies_lighting_rigs(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("#version 2\n3 * { x 1.5 } box\n")
    qtbot.waitUntil(lambda: tab.outcome is not None and window.viewport.bounds() is not None, timeout=30000)
    window.light_actions.apply_rig("Studio softbox")
    assert "light rig_key {" in tab.text() and "environment {" in tab.text()
    window.light_actions.apply_rig("Night neon")  # replaces the first rig; sets the look it is made for
    assert "rig_key" not in tab.text() and "light rig_magenta {" in tab.text()
    assert window.render_view.controls.look.currentText() == "Neon"
    qtbot.waitUntil(lambda: window.lights.list.count() == 3, timeout=30000)
    tab.editor.undo()
    assert "rig_magenta" not in tab.text() and "rig_key" in tab.text()


def test_light_templates_build(tmp_path: object) -> None:
    import numpy as np  # noqa: PLC0415

    from structura.core.build.api import build_scene  # noqa: PLC0415
    from structura.core.lang.api import compile_script  # noqa: PLC0415
    from structura.core.scene.light_script import KINDS, light_text  # noqa: PLC0415

    blocks = "\n".join(light_text(kind, f"l{kind}", np.zeros(3), np.ones(3)) for kind in KINDS)
    declarations = build_scene(compile_script(f"#version 2\n{blocks}\nbox\n").program).scene.declarations
    assert declarations is not None and [light.type for light in declarations.lights] == list(KINDS)


def test_lights_panel_edits_a_light_block(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("#version 2\nlight key { type spot position [0 4 0] target [0 0 0] cone 20 }\nbox\n")
    panel = window.lights
    qtbot.waitUntil(lambda: panel.list.count() == 1, timeout=30000)
    panel.list.setCurrentRow(0)
    assert panel.form is not None and "cone" in panel.form.widgets and "direction" not in panel.form.widgets
    panel.form.widgets["cone"].setValue(35.0)  # type: ignore[attr-defined]
    panel.form.widgets["position"].setText("[1 5 2]")  # type: ignore[attr-defined]
    panel.form.widgets["position"].editingFinished.emit()  # type: ignore[attr-defined]
    qtbot.waitUntil(lambda: "cone 35" in tab.text(), timeout=5000)
    assert "position [1 5 2]" in tab.text() and "target [0 0 0]" in tab.text() and tab.text().count("light key") == 1


def test_materials_panel_offers_glass_fields_but_no_debug_models(qtbot: QtBot, window: MainWindow) -> None:
    panel = window.materials
    models = [panel.form.widgets["model"].itemText(i) for i in range(panel.form.widgets["model"].count())]  # type: ignore[attr-defined]
    assert "wireframe" in models and not any(m.startswith("debug") for m in models)
    for key in ("transmission_roughness", "attenuation_distance", "thin_walled", "anisotropy", "opacity"):
        assert key in panel.form.widgets
