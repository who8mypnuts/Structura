"""Saving and opening .structura projects in the window (docs/07 §8)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtWidgets import QFileDialog
from pytestqt.qtbot import QtBot

from structura.core.scene.camera import Camera
from structura.services.settings import SettingsService
from structura.ui.app_window import MainWindow

SCRIPT = "set maxdepth 6\nr\nrule r { { x 1.5 } r box }\n"


def test_save_project_then_open_it_restores_seed_overrides_and_camera(
    qtbot: QtBot, tmp_path: Path, window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText(SCRIPT)
    tab.seed, tab.render_overrides = 5, {"max_bounces": 11}
    qtbot.waitUntil(lambda: tab.outcome is not None, timeout=20000)
    camera = Camera((3.0, 4.0, 25.0), (1.0, 0.0, 0.0), fov_y_deg=28.0)
    window.viewport.set_camera(camera)
    target = tmp_path / "spiral.structura"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), ""))
    window.registry.trigger("file.save_project")
    data = json.loads(target.read_text())
    assert data["seed"] == 5 and data["render"] == {"max_bounces": 11} and data["script"]["text"] == SCRIPT
    assert tab.title == "spiral.structura" and not tab.modified

    other = MainWindow(SettingsService(tmp_path / "other.ini"))
    qtbot.addWidget(other, before_close_func=lambda w: None)
    opened = other.docs.open_file(target)
    assert opened is not None and opened.seed == 5 and opened.render_overrides == {"max_bounces": 11}
    assert other.render_settings.overrides == {"max_bounces": 11}
    qtbot.waitUntil(lambda: opened.outcome is not None and opened.camera_applied, timeout=20000)
    restored = other.viewport.camera()
    assert np.allclose(restored.eye, camera.eye, atol=1e-4) and restored.fov_y_deg == pytest.approx(28.0)


def test_open_from_render_restores_script_seed_and_settings(window: MainWindow, tmp_path: Path) -> None:
    from structura.cli.main import main  # noqa: PLC0415

    script = tmp_path / "scene.es"
    script.write_text("set raytracer::max-threads 1\n{ color #f80 } sphere\n")
    out = tmp_path / "scene.png"
    argv = ["render", str(script), "-o", str(out), "--size", "24x16", "--device", "cpu", "--seed", "9"]
    assert main([*argv, "--integrator", "ao", "--samples", "2"]) == 0
    tab = window.projects.open_render(out)
    assert tab is not None and tab.text() == script.read_text() and tab.seed == 9
    assert tab.initial_camera is not None and tab.display_name == "scene.es" and tab.path is None
