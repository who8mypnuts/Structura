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
    _built(qtbot, window)
    window.render_view.samples.setValue(2)
    window.render_actions.start_render()
    qtbot.waitUntil(lambda: window.render_view.last is not None and window.render_view.last.fraction >= 1.0,
                    timeout=120000)  # fmt: skip
    targets = iter([tmp_path / "image.png", tmp_path / "report.html", tmp_path / "report"])
    monkeypatch.setattr(SavePaths, "ask", lambda *a, **k: (next(targets), a[5][0]))
    window.registry.trigger("render.save")
    qtbot.waitUntil((tmp_path / "image.png").exists, timeout=30000)
    qtbot.waitUntil(lambda: any("image.png" in t.label.text() for t in window.toasts.toasts), timeout=10000)
    assert window.toasts.toasts[-1].button is not None  # "Show in Folder"
    window.registry.trigger("render.report")
    qtbot.waitUntil((tmp_path / "report.html").exists, timeout=30000)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
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
    assert dialog.form.values()["unit_scale"] == 25.4 and dialog.presets.count() == 2


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
