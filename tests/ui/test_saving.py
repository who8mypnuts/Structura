"""Save As flows (docs/14 §7 Paths): exports, renders and render reports go where the user chooses."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QDialog
from pytestqt.qtbot import QtBot

from structura.ui import save_paths
from structura.ui.app_window import MainWindow
from structura.ui.dialogs.export_dialog import ExportDialog
from structura.ui.export_actions import file_filter
from structura.ui.save_paths import SavePaths, with_extension

SCRIPT = "{ color #f80 } sphere\n3 * { x 1.2 } box\n"


class _Settings:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}

    def value(self, key: str, default: object = None) -> object:
        return self.values.get(key, default)

    def set_value(self, key: str, value: object) -> None:
        self.values[key] = value


def test_dialogs_start_in_the_last_folder_then_the_scripts_then_documents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(save_paths.platformdirs, "user_documents_dir", lambda: str(tmp_path / "docs"))
    paths = SavePaths(_Settings())
    assert paths.folder("export") == tmp_path / "docs" / "Structura"  # never the working directory
    script = tmp_path / "scripts" / "a.es"
    script.parent.mkdir()
    assert paths.suggest("export", "a.obj", script) == script.parent / "a.obj"
    paths.remember("export", tmp_path / "out" / "b.obj")
    assert paths.folder("export", script) == script.parent  # the remembered folder does not exist
    (tmp_path / "out").mkdir()
    assert paths.folder("export", script) == tmp_path / "out"
    assert paths.folder("report", script) == script.parent  # each kind has its own memory
    assert (
        with_extension(Path("x"), (".glb",)) == Path("x.glb")
        and with_extension(Path("x.GLB"), (".glb",)).name == "x.GLB"
    )


def _built(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText(SCRIPT)
    qtbot.waitUntil(lambda: tab.outcome is not None, timeout=30000)


def test_export_as_asks_where_and_in_which_format(
    qtbot: QtBot, window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _built(qtbot, window)
    exporters = {e.name: e for e in window.exports.exporters()}
    asked: list[tuple[str, list[str]]] = []

    def ask(self: SavePaths, parent: object, kind: str, title: str, suggestion: Path, filters: list[str],
            selected: str = "") -> tuple[Path, str]:  # fmt: skip
        asked.append((kind, filters))
        assert suggestion.is_absolute()
        return tmp_path / "chosen" / "model.glb", file_filter(exporters["obj"])  # typed .glb, OBJ type selected

    monkeypatch.setattr(SavePaths, "ask", ask)
    opened: list[ExportDialog] = []
    monkeypatch.setattr(ExportDialog, "exec", lambda d: (opened.append(d), d._accept(), d.result())[2])
    done: list[object] = []
    window.exports.service.finished.connect(done.append)
    window.registry.trigger("file.export_as")
    assert asked[0][0] == "export" and len(asked[0][1]) == len(exporters)  # every format on offer
    assert opened[0].exporter.name == "gltf" and opened[0].path == tmp_path / "chosen" / "model.glb"
    assert opened[0].result() == QDialog.DialogCode.Accepted
    qtbot.waitUntil(lambda: bool(done), timeout=30000)
    assert (tmp_path / "chosen" / "model.glb").stat().st_size > 500


def test_render_save_and_reports_go_to_the_chosen_files(
    qtbot: QtBot, window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from structura.ui import render_actions  # noqa: PLC0415
    from structura.ui.dialogs.render_output import RenderOutput  # noqa: PLC0415

    _built(qtbot, window)
    window.render_view.samples.setValue(2)
    window.render_actions.start_render()
    qtbot.waitUntil(lambda: window.render_view.last is not None and window.render_view.last.fraction >= 1.0,
                    timeout=120000)  # fmt: skip
    image, beside = tmp_path / "out" / "image.png", tmp_path / "out" / "image-report.md"
    monkeypatch.setattr(render_actions, "choose_output", lambda *a, **k: RenderOutput(image, beside))
    window.registry.trigger("render.save")
    qtbot.waitUntil(lambda: beside.exists() and "image.png" in beside.read_text(encoding="utf-8"), timeout=30000)
    assert image.exists()
    qtbot.waitUntil(lambda: any("image.png" in t.label.text() for t in window.toasts.toasts), timeout=10000)
    assert window.toasts.toasts[-1].button is not None  # "Show in Folder"
    targets = iter([tmp_path / "report.html", tmp_path / "report"])
    asked: list[Path] = []
    monkeypatch.setattr(SavePaths, "ask", lambda *a, **k: (asked.append(a[4]), next(targets), a[5][0])[1:])
    window.registry.trigger("render.report")
    assert asked[-1].parent == image.parent  # a report on its own starts beside the saved image
    report = tmp_path / "report.html"
    qtbot.waitUntil(lambda: report.exists() and "</html>" in report.read_text(encoding="utf-8"), timeout=30000)
    html = report.read_text(encoding="utf-8")
    assert "image.png" in html and "Visible objects" in html
    window.registry.trigger("render.report")  # no extension typed: the chosen type's (PDF, listed first)
    qtbot.waitUntil((tmp_path / "report.pdf").exists, timeout=30000)


def test_toasts_stack_and_respect_reduced_motion(window: MainWindow) -> None:
    window.settings.set_value("appearance/reduce_motion", True)
    for n in range(5):
        window.toasts.show(f"notice {n}")
    texts = [t.label.text() for t in window.toasts.toasts]
    assert texts == ["notice 2", "notice 3", "notice 4"]  # at most three, newest at the bottom
    assert all(t.effect.opacity() == 1.0 for t in window.toasts.toasts)  # no fade
    tops = [t.y() for t in window.toasts.toasts]
    assert tops == sorted(tops) and all(t.x() + t.width() <= window.width() for t in window.toasts.toasts)


def test_export_sheet_saves_and_loads_presets(
    qtbot: QtBot, window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from structura.export import presets  # noqa: PLC0415

    monkeypatch.setattr(presets.platformdirs, "user_config_dir", lambda _name: str(tmp_path / "config"))
    _built(qtbot, window)
    exporters = {e.name: e for e in window.exports.exporters()}
    tab = window.tabs.current()
    dialog = ExportDialog(exporters["stl"], tmp_path / "a.stl", tab.outcome.scene, {}, lambda e, p: None, window)
    qtbot.addWidget(dialog)
    dialog.form.set_values({"unit_scale": 25.4})
    dialog.save_preset_as("Inches")
    dialog.form.set_values({"unit_scale": 1.0})
    dialog.presets.setCurrentIndex(dialog.presets.findData("Inches"))
    dialog._load_preset()
    assert dialog.form.values()["unit_scale"] == 25.4 and dialog.presets.count() == 3  # —, Inches, the built-in


def test_template_run_after_asks_once_then_runs(
    window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PySide6.QtWidgets import QMessageBox  # noqa: PLC0415

    asked: list[str] = []
    started: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: (asked.append(a[2]), QMessageBox.StandardButton.Yes)[1]
    )
    monkeypatch.setattr(window.processes, "start", lambda command, cwd: started.append(command))
    target = tmp_path / "scene.sc"
    window.exports.run_after("Sunflow-Colored", target)
    window.exports.run_after("Sunflow-Colored", target)
    assert len(asked) == 1 and len(started) == 2 and str(target) in started[0]
    window.exports.run_after("povray", target)  # no runAfter: nothing happens
    assert len(started) == 2


def test_the_export_sheet_estimates_the_file_size(qtbot: QtBot, window: MainWindow, tmp_path: Path) -> None:
    _built(qtbot, window)
    exporters = {e.name: e for e in window.exports.exporters()}
    tab = window.tabs.current()
    dialog = ExportDialog(exporters["stl"], tmp_path / "a.stl", tab.outcome.scene, {}, lambda e, p: None, window)
    qtbot.addWidget(dialog)
    window.exports.estimating = dialog
    window.exports._estimate(tab.outcome.scene, dialog, dialog.form.values())
    qtbot.waitUntil(lambda: dialog.estimate.text().startswith("≈"), timeout=30000)
    assert "KB" in dialog.estimate.text() or "MB" in dialog.estimate.text()


def test_the_template_sheet_describes_previews_edits_and_autosaves(
    qtbot: QtBot, window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from structura.export.templates import template_file  # noqa: PLC0415

    monkeypatch.setattr(template_file, "user_template_dir", lambda: tmp_path / "mine")
    _built(qtbot, window)
    exporter = {e.name: e for e in window.exports.exporters()}["template"]
    tab = window.tabs.current()
    dialog = ExportDialog(exporter, tmp_path / "a.pov", tab.outcome.scene, {"template": "povray"},
                          lambda e, p: None, window, window.themes.theme)  # fmt: skip
    qtbot.addWidget(dialog)
    pages = dialog.pages
    assert pages is not None and pages.description.text() and "<template" in pages.editor.toPlainText()
    window.exports.estimating = dialog
    window.exports._preview(tab.outcome.scene, dialog.form.values())
    qtbot.waitUntil(lambda: bool(pages.preview.toPlainText()), timeout=30000)
    pages.editor.setPlainText(pages.editor.toPlainText().replace("#declare", "// mine\n#declare", 1))
    assert pages.save_as("Mine")
    assert dialog.form.values()["template"] == "Mine" and "// mine" in pages.editor.toPlainText()
    exporter.refresh()  # type: ignore[attr-defined]
    monkeypatch.undo()
    exporter.refresh()  # type: ignore[attr-defined]
    window.exports.autosave_script(tab, tmp_path / "a.pov")
    saved = tmp_path / "a.es"
    qtbot.waitUntil(lambda: saved.exists() and f"set seed {tab.seed}" in saved.read_text(encoding="utf-8"),
                    timeout=10000)  # fmt: skip


def test_blender_exports_offer_open_in_blender(
    window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from structura.ui import export_actions  # noqa: PLC0415
    from structura.ui import external_apps as blender_app  # noqa: PLC0415

    fake = tmp_path / "blender"
    fake.write_text("")
    assert blender_app.find_blender(str(fake)) == str(fake)
    assert blender_app.find_blender(str(tmp_path / "missing")) is None
    window.settings.set_value("paths/blender", str(fake))
    started: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(window.processes, "start_program", lambda p, args, cwd: started.append((p, args)))
    script = tmp_path / "scene.py"
    window.exports._offer_blender(script)
    toast = window.toasts.toasts[-1]
    assert toast.button is not None and toast.button.text() == "Open in Blender"
    assert "Blender was not found" not in window.status.currentMessage()
    toast.button.click()
    assert started == [(str(fake), ["--python", str(script)])]
    monkeypatch.setattr(export_actions, "find_blender", lambda _configured: None)
    window.exports.open_in_blender(script)
    assert "Blender was not found" in window.status.currentMessage()


def test_save_as_legacy_writes_a_1_5_copy_with_the_camera(
    qtbot: QtBot, window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("#version 2\ncamera { position [0 0 10] target [0 0 0] fov 40 }\n{ x 1 } cone\nbox\n")
    target = tmp_path / "old.es"
    monkeypatch.setattr(SavePaths, "ask", lambda *a, **k: (target, a[5][0]))
    window.registry.trigger("file.save_legacy")
    qtbot.waitUntil(lambda: target.exists() and "box" in target.read_text(encoding="utf-8"), timeout=10000)
    text = target.read_text(encoding="utf-8")
    assert "set translation" in text and "cone" not in text and "#version" not in text
    qtbot.waitUntil(lambda: any("Legacy copy:" in line for line, _ in window.console.records), timeout=5000)


def test_exports_are_listed_in_the_queue(qtbot: QtBot, window: MainWindow, tmp_path: Path) -> None:
    from structura.services.export import ExportRequest  # noqa: PLC0415

    _built(qtbot, window)
    tab = window.tabs.current()
    target = tmp_path / "a.stl"
    window.exports.service.request(ExportRequest(tab.outcome.scene, target, "stl"))
    entry = window.render_queue.track_export("STL", target)
    assert entry.state == "exporting" and entry.request is None
    qtbot.waitUntil(lambda: entry.state == "done", timeout=30000)
    assert entry.fraction == 1.0
    window.queue_panel.refresh()
    assert window.queue_panel.tree.topLevelItem(0).text(1) == "done"


def test_the_output_dialog_puts_the_chosen_report_beside_the_image(window: MainWindow, tmp_path: Path) -> None:
    from structura.ui.dialogs.render_output import RenderOutputDialog, image_path, report_beside  # noqa: PLC0415

    paths = SavePaths(window.settings)
    dialog = RenderOutputDialog(paths, tmp_path / "tree.png", "Final Render", "Render", ("Final", "Print 4K"), window)
    assert [dialog.report.itemData(i) for i in range(5)] == ["", ".pdf", ".html", ".md", ".txt"]
    dialog.report.setCurrentIndex(dialog.report.findData(".txt"))
    dialog.path.setText(str(tmp_path / "renders" / "spiral"))
    assert "spiral-report.txt" in dialog.where.text()
    dialog._accept()
    out = dialog.output()
    assert out is not None and out.image == tmp_path / "renders" / "spiral.png" and out.preset == "Final"
    assert out.report == tmp_path / "renders" / "spiral-report.txt" and out.save
    assert window.settings.value("render/report_format") == ".txt"  # remembered for the next time
    again = RenderOutputDialog(paths, tmp_path / "x.png", "Save Render", "Save", parent=window)
    assert again.report.currentData() == ".txt" and again.preset is None
    again.report.setCurrentIndex(0)
    assert again.output().report is None and again.where.text() == ""  # type: ignore[union-attr]
    assert image_path("a.exr") == Path("a.exr") and report_beside(Path("/r/a.exr"), ".html") == Path("/r/a-report.html")


def test_a_final_render_asks_where_then_saves_image_and_report(
    qtbot: QtBot, window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from structura.ui import render_actions  # noqa: PLC0415
    from structura.ui.dialogs.render_output import RenderOutput  # noqa: PLC0415

    _built(qtbot, window)
    controls = window.render_view.controls
    finals: list[bool] = []
    monkeypatch.setattr(window.render_actions, "final_render", lambda: finals.append(True))
    controls.preset.setCurrentText("Final")
    controls.render_button.click()  # the Render button with a final preset asks where to save first
    assert finals == [True]
    monkeypatch.undo()
    offered: list[tuple[str, ...]] = []

    def choose(*args: object) -> RenderOutput:
        offered.append(args[5])  # type: ignore[arg-type]
        return RenderOutput(tmp_path / "final.png", tmp_path / "final-report.html", "Custom")

    monkeypatch.setattr(render_actions, "choose_output", choose)
    controls.samples.setValue(2)  # Custom: the tool bar's own settings (a quick test)
    window.registry.trigger("render.final")
    assert offered[0][0] == "Custom" and "Final" in offered[0] and "Print 4K" in offered[0]
    report = tmp_path / "final-report.html"
    qtbot.waitUntil(lambda: report.exists() and "</html>" in report.read_text(encoding="utf-8"), timeout=120000)
    assert (tmp_path / "final.png").exists() and "final.png" in report.read_text(encoding="utf-8")
    assert window.render_actions.pending is None
