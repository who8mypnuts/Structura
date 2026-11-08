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


def test_light_templates_build(tmp_path: object) -> None:
    import numpy as np  # noqa: PLC0415

    from structura.core.build.api import build_scene  # noqa: PLC0415
    from structura.core.lang.api import compile_script  # noqa: PLC0415
    from structura.core.scene.light_script import KINDS, light_text  # noqa: PLC0415

    blocks = "\n".join(light_text(kind, f"l{kind}", np.zeros(3), np.ones(3)) for kind in KINDS)
    declarations = build_scene(compile_script(f"#version 2\n{blocks}\nbox\n").program).scene.declarations
    assert declarations is not None and [light.type for light in declarations.lights] == list(KINDS)
