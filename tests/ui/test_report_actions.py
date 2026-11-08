"""The Render Report action (docs/09 §11): a save dialog, then every format."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PySide6.QtWidgets import QFileDialog
from pytestqt.qtbot import QtBot

from structura.core.scene.camera import Camera
from structura.render.api import RenderProgress
from structura.render.report import ScenePrepStats
from structura.services.render import RenderUpdate
from structura.ui.app_window import MainWindow

SCRIPT = "set maxdepth 6\nr\nrule r { { x 1.2 } r box }\n{ x 3 } sphere\n"
STATS = ScenePrepStats(render_primitives=5, triangles=0, bvh_nodes=3, materials=1, emitters=0,
                       bounds_lo=(0.0, 0.0, 0.0), bounds_hi=(3.6, 1.0, 1.0))  # fmt: skip


def _rendered(window: MainWindow, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText(SCRIPT)
    qtbot.waitUntil(lambda: tab.outcome is not None, timeout=20000)
    settings = window.render_view.settings(48, 32)
    image = np.full((32, 48, 3), 0.2, np.float32)
    update = RenderUpdate(RenderProgress(image, settings.samples, 1.25), "cpu CPU (Numba)", settings.samples,
                          settings=settings, camera=Camera((0, 0, 10), (0, 0, 0)), scene_stats=STATS)  # fmt: skip
    monkeypatch.setattr(window.render_view, "last", update)


def test_report_needs_a_render_first(window: MainWindow) -> None:
    window.reports.save_dialog()  # no render yet: a status message, not a crash
    assert "Render the view first" in window.status.currentMessage()


@pytest.mark.parametrize(
    ("suffix", "marker"), [(".html", "<h1>Structura render report</h1>"), (".md", "# Structura render report"),
                           (".txt", "STRUCTURA RENDER REPORT"), (".json", '"generated"')],
)  # fmt: skip
def test_every_text_format_has_the_scene_camera_and_settings(
    window: MainWindow, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, suffix: str, marker: str
) -> None:
    _rendered(window, qtbot, monkeypatch)
    target = tmp_path / f"report{suffix}"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), ""))
    window.reports.save_dialog()
    text = target.read_text()
    assert marker in text
    assert "bvh_nodes" in text.lower().replace(" ", "_")  # scene_stats, however the format spells the label
    assert "Render the view first" not in window.status.currentMessage()


def test_pdf_report_is_a_real_pdf(
    window: MainWindow, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _rendered(window, qtbot, monkeypatch)
    target = tmp_path / "report.pdf"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), ""))
    window.reports.save_dialog()
    assert target.read_bytes().startswith(b"%PDF")
