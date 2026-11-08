"""Every export / save / report dialog suggests the open script's folder (docs/14 §9): a regression test
for each call site, since a bare file name would otherwise open relative to the working directory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest
from PySide6.QtWidgets import QFileDialog
from pytestqt.qtbot import QtBot

from structura.render.api import RenderProgress
from structura.render.settings import RenderSettings
from structura.services.render import RenderUpdate
from structura.ui.app_window import MainWindow

SCRIPT = "{ s 0.6 } box\n"


def _open_script(window: MainWindow, qtbot: QtBot, tmp_path: Path) -> Path:
    path = tmp_path / "scene" / "spire.es"
    path.parent.mkdir()
    path.write_text(SCRIPT)
    tab = window.docs.open_file(path)
    assert tab is not None
    qtbot.waitUntil(lambda: tab.outcome is not None, timeout=20000)
    return path.parent


def _capture_directory(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Stand in for the native Save dialog: records the suggested path, answers "cancelled"."""
    seen: dict[str, str] = {}

    def fake(_parent: Any, _title: str, directory: str, _filter: str) -> tuple[str, str]:
        seen["directory"] = directory
        return "", ""

    monkeypatch.setattr(QFileDialog, "getSaveFileName", fake)
    return seen


def test_export_suggests_the_script_s_folder(
    window: MainWindow, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = _open_script(window, qtbot, tmp_path)
    seen = _capture_directory(monkeypatch)
    window.exports.start("obj")
    assert Path(seen["directory"]).parent == folder


def test_save_script_as_suggests_the_script_s_folder(
    window: MainWindow, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = _open_script(window, qtbot, tmp_path)
    seen = _capture_directory(monkeypatch)
    window.docs.save_as()
    assert Path(seen["directory"]).parent == folder


def test_save_project_as_suggests_the_script_s_folder(
    window: MainWindow, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = _open_script(window, qtbot, tmp_path)
    seen = _capture_directory(monkeypatch)
    window.projects.save_as()
    assert Path(seen["directory"]).parent == folder


def test_save_render_suggests_the_script_s_folder(
    window: MainWindow, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = _open_script(window, qtbot, tmp_path)
    window.render_view.last = RenderUpdate(RenderProgress(np.zeros((4, 4, 3), np.float32), 1, 0.1), "cpu", 1)
    seen = _capture_directory(monkeypatch)
    window.render_view.save_dialog()
    assert Path(seen["directory"]).parent == folder


def test_render_report_suggests_the_script_s_folder(
    window: MainWindow, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = _open_script(window, qtbot, tmp_path)
    settings = RenderSettings(width=4, height=4)
    window.render_view.last = RenderUpdate(RenderProgress(np.zeros((4, 4, 3), np.float32), 1, 0.1), "cpu", 1,
                                           settings=settings)  # fmt: skip
    seen = _capture_directory(monkeypatch)
    window.reports.save_dialog()
    assert Path(seen["directory"]).parent == folder
