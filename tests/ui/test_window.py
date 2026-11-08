"""The main window end to end: edit → analyse → build → preview, problems, commands, themes (docs/14)."""

from __future__ import annotations

from pytestqt.qtbot import QtBot

from structura.core.build.api import build_scene
from structura.core.lang.api import compile_script
from structura.export.api import EXPORTERS
from structura.ui.app_window import MainWindow
from structura.ui.command_palette import fuzzy_score

SCRIPT = "set maxdepth 30\nR\nrule R { { x 1 rz 10 s 0.97 } R box }\n"


def test_typing_a_script_builds_it_live(qtbot: QtBot, window: MainWindow) -> None:
    expected = len(build_scene(compile_script(SCRIPT).program).scene)
    tab = window.docs.new_script()
    tab.editor.setPlainText(SCRIPT)
    qtbot.waitUntil(lambda: tab.outcome is not None and len(tab.outcome.scene) == expected, timeout=60000)
    assert window.status.labels["objects"].text() == f"{expected} objects"
    assert window.stats.labels["Objects"].text().startswith(str(expected))
    assert [window.outline.tree.topLevelItem(i).text(0) for i in range(window.outline.tree.topLevelItemCount())] == [
        "r"
    ]


def test_errors_reach_the_editor_and_the_problems_panel(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("rule R { box \nR\n")
    qtbot.waitUntil(lambda: bool(tab.editor.diagnostics), timeout=10000)
    assert tab.editor.diagnostics[0].code == "E001"
    assert window.problems.topLevelItemCount() == 1
    assert list(tab.editor.gutter.markers) == [2]  # the error is at the end of the text (line 3)


def test_seed_changes_rebuild(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("R\nrule R w 1 { box }\nrule R w 1 { sphere }\n")
    qtbot.waitUntil(lambda: tab.outcome is not None, timeout=60000)
    first = tab.outcome
    window.build_actions.next_seed()
    qtbot.waitUntil(lambda: tab.outcome is not first, timeout=60000)
    assert tab.seed == 1 and window.header.seed.value() == 1


def test_every_command_is_in_the_registry_once_and_menus_exist(window: MainWindow) -> None:
    ids = [c.id for c in window.registry.commands()]
    assert len(ids) == len(set(ids)) and {"build.run", "render.start", "view.palette", "file.save"} <= set(ids)
    titles = [a.text().replace("&", "") for a in window.menuBar().actions()]
    assert titles[:5] == ["File", "Edit", "Insert", "View", "Build"]
    assert window.registry.action("build.run").shortcut().toString() == "F5"


def test_command_palette_filters_fuzzily(window: MainWindow) -> None:
    assert fuzzy_score("bld", "Build: Build") is not None
    assert fuzzy_score("xyz", "Build: Build") is None
    window.command_palette.open()
    window.command_palette.input.setText("seed")
    shown = [window.command_palette.list.item(i).text() for i in range(window.command_palette.list.count())]
    assert shown and "Seed" in shown[0]  # exact substring matches rank first


def test_switching_theme_restyles_the_editor(window: MainWindow) -> None:
    tab = window.docs.new_script()
    window.themes.set_theme("nord")
    assert window.themes.theme.meta.id == "nord"
    keyword = tab.editor.highlighter._format("keyword")
    assert keyword.foreground().color().name().upper() == window.themes.theme["syntax.keyword"][:7].upper()
    window.dialogs.toggle_theme()
    assert window.themes.theme.meta.id == "nord-light"


def test_compute_preview_shows_the_built_scene(qtbot: QtBot, window: MainWindow) -> None:
    assert window.viewport.compute_mode  # the offscreen platform cannot host a child QOpenGLWidget
    tab = window.docs.new_script()
    tab.editor.setPlainText(SCRIPT)
    qtbot.waitUntil(lambda: window.viewport.compute.image is not None, timeout=120000)
    compute = window.viewport.compute
    assert compute.image is not None and compute.image.width() > 8
    assert compute.device_label.startswith("cpu") and compute.badge_text() == "CPU preview"  # no GPU here
    compute.device_label = "cuda NVIDIA GeForce GTX 1660"
    assert compute.badge_text() == "CUDA preview"


def test_go_to_definition_and_insert_snippets(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("R\nrule R { box }\n")
    qtbot.waitUntil(lambda: tab.analysis is not None and tab.analysis.version == tab.version, timeout=10000)
    window.docs.go_to_definition("R")
    assert tab.editor.textCursor().position() == 2
    insert = [a.text() for a in window.menuBar().actions() if a.text().replace("&", "") == "Insert"]
    assert insert
    window.registry.trigger("insert.0")
    assert "x 1 // translations" in tab.text()


def test_files_changed_on_disk_reload_when_unmodified(qtbot: QtBot, window: MainWindow, tmp_path: object) -> None:
    from pathlib import Path  # noqa: PLC0415

    path = Path(str(tmp_path)) / "scene.es"
    path.write_text("box\n")
    tab = window.docs.open_file(path)
    path.write_text("sphere\n")
    qtbot.waitUntil(lambda: tab.text() == "sphere\n", timeout=10000)
    assert not tab.modified


def test_export_menu_lists_every_format_and_exports_in_the_background(
    qtbot: QtBot, window: MainWindow, tmp_path: object
) -> None:
    from pathlib import Path  # noqa: PLC0415

    from structura.services.export import ExportRequest  # noqa: PLC0415

    titles = [a.text() for a in window.menuBar().actions()]
    assert any(t.replace("&", "") == "Export" for t in titles)
    assert {"export.usd", "export.gltf", "export.blender", "export.template"} <= {
        c.id for c in window.registry.commands()
    }
    tab = window.docs.new_script()
    tab.editor.setPlainText(SCRIPT)
    qtbot.waitUntil(lambda: tab.outcome is not None, timeout=30000)
    done: list[object] = []
    window.exports.service.finished.connect(done.append)
    target = Path(str(tmp_path)) / "out.glb"
    window.exports.service.request(ExportRequest(tab.outcome.scene, target, "gltf", {}))
    qtbot.waitUntil(lambda: bool(done), timeout=30000)
    assert target.exists() and target.stat().st_size > 1000


def test_variation_explorer_fills_cells_and_adopts_a_seed(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("R\nrule R w 1 { { x 1 } R box }\nrule R w 1 { sphere }\n")
    qtbot.waitUntil(lambda: tab.analysis is not None and tab.analysis.ok and tab.analysis.version == tab.version,
                    timeout=20000)  # fmt: skip
    explorer = window.variations
    explorer.explore(tab.analysis.program, list(range(100, 109)))
    qtbot.waitUntil(lambda: all(not b.icon().isNull() for b in explorer.cells), timeout=120000)
    explorer.cells[4].click()
    assert tab.seed == 104 and window.header.seed.value() == 104


def test_export_menu_offers_every_registered_exporter_once(window: MainWindow) -> None:
    names = [e.name for e in window.exports.exporters()]
    assert sorted(names) == sorted(EXPORTERS) and names[:3] == ["obj", "ply", "stl"]


def test_convert_to_v2_rewrites_the_script_in_one_undo_step(window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("rule tube { box }\ntube\n")
    window.registry.trigger("edit.convert_v2")
    assert tab.text().startswith("#version 2\nrule tube_rule")
    tab.editor.undo()
    assert tab.text() == "rule tube { box }\ntube\n"


def test_parameter_variations_adopt_and_expand(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("#define n 6 (int:2-12)\n#define s 1 (float:0.5-2)\nn * { x s } box\n")
    qtbot.waitUntil(lambda: tab.analysis is not None and tab.analysis.ok and tab.analysis.version == tab.version,
                    timeout=20000)  # fmt: skip
    explorer = window.variations
    explorer.mode.setCurrentIndex(explorer.mode.findData("params"))
    window.registry.trigger("build.variations")
    assert explorer.cell_params[0] == {"n": 6.0, "s": 1.0}  # the first cell is the current state
    assert all(2 <= p["n"] <= 12 and p["n"] == int(p["n"]) for p in explorer.cell_params if p)
    qtbot.waitUntil(lambda: all(not b.icon().isNull() for b in explorer.cells), timeout=120000)
    chosen = explorer.cell_params[4]
    explorer.cells[4].click()
    assert tab.params == chosen
    explorer.expand(4)
    assert explorer.cell_params[0] == chosen and explorer._spread == 0.125
