"""Tab handling (PLAN QoL-1) and the render frame with its viewport guide (PLAN QoL-2)."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QMessageBox
from pytestqt.qtbot import QtBot

from structura.core.scene.camera import Camera
from structura.ui.app_window import MainWindow
from structura.ui.render_view.presets import fitted, frame_size, guide_rect
from structura.ui.save_paths import SavePaths

BUTTONS = QMessageBox.StandardButton


def _modified(window: MainWindow, text: str = "box\n") -> int:
    tab = window.docs.new_script()
    tab.editor.setPlainText(text)
    tab.editor.document().setModified(True)  # (setPlainText starts a clean document, as opening a file does)
    return window.tabs.indexOf(tab)


def test_closing_a_modified_tab_offers_to_save_it(
    window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    index = _modified(window, "// keep me\nbox\n")
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: BUTTONS.Cancel)
    assert not window.tabs.close_tab(index) and window.tabs.count() == 1
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: BUTTONS.Save)
    monkeypatch.setattr(SavePaths, "ask", lambda *a, **k: None)  # the Save As dialog is cancelled …
    assert not window.tabs.close_tab(index) and window.tabs.count() == 1  # … so the tab stays
    target = tmp_path / "kept.es"
    monkeypatch.setattr(SavePaths, "ask", lambda *a, **k: (target, ""))
    assert window.tabs.close_tab(index) and window.tabs.count() == 0
    assert target.read_text() == "// keep me\nbox\n"


def test_close_others_and_to_the_right_and_middle_click(window: MainWindow, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: BUTTONS.Discard)
    for _ in range(4):
        _modified(window)
    assert window.tabs.close_tabs(list(range(2, 4))) and window.tabs.count() == 2  # "Close to the Right" of #1
    bar = window.tabs.tabBar()
    centre = QPointF(bar.tabRect(0).center())
    release = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, centre, centre, Qt.MouseButton.MiddleButton,
                          Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)  # fmt: skip
    QApplication.sendEvent(bar, release)
    assert window.tabs.count() == 1
    window.docs.tab_menu(QPoint(5, 5))  # the context menu builds (and would pop up) without errors


def test_frames_guides_and_fitted_cameras() -> None:
    assert frame_size("16:9", (800, 600), 1920, (640, 480), (100, 100)) == (1920, 1080)
    assert frame_size("9:16", (800, 600), 1920, (640, 480), (100, 100)) == (1080, 1920)
    assert frame_size("Script", (800, 600), 1920, (1234, 567), (100, 100)) == (1234, 567)
    assert frame_size("Custom", (800, 600), 1920, (640, 480), (300, 200)) == (300, 200)
    assert guide_rect(1.0, (800, 400)) == (200.0, 0.0, 400.0, 400.0)  # a square in a wide view: full height
    assert guide_rect(4.0, (800, 400)) == (0.0, 100.0, 800.0, 200.0)  # wider: full width, letterboxed
    camera = Camera((0.0, 0.0, 10.0), (0.0, 0.0, 0.0), fov_y_deg=40.0)
    assert fitted(camera, 1.0, 2.0) is camera and fitted(camera, 4.0, 2.0).fov_y_deg < 40.0


def test_the_viewport_shows_the_render_frame(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("#version 2\nrender { size 400x100 }\nbox\n")
    qtbot.waitUntil(lambda: tab.outcome is not None, timeout=30000)
    controls = window.render_view.controls
    assert window.viewport.overlay.frame is None  # the viewport's own shape: no guide
    controls.frame.setCurrentText("1:1")
    assert window.viewport.overlay.frame is not None and window.viewport.overlay.frame[0] == 1.0
    width, height = window.render_actions.render_size()
    assert width == height
    controls.frame.setCurrentText("Script")
    assert window.render_actions.render_size() == (400, 100) and window.viewport.overlay.frame[1] == "400 × 100"
    source = window.render_actions.render_source()
    assert source is not None and (source[2].width, source[2].height) == (400, 100)
