"""Render ▸ Turntable… and Camera Path from Saved Views… key the timeline (PLAN F2)."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QDialog, QInputDialog
from pytestqt.qtbot import QtBot

from structura.core.scene.camera import Camera
from structura.ui.app_window import MainWindow
from structura.ui.dialogs.turntable_dialog import TurntableDialog


def test_turntable_keys_a_loop(qtbot: QtBot, window: MainWindow, monkeypatch: pytest.MonkeyPatch) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("box\n")
    qtbot.waitUntil(lambda: tab.outcome is not None, timeout=30000)

    def accept(dialog: TurntableDialog) -> int:
        """Fills the dialog (2 s at 12 fps, no render) and accepts it."""
        dialog.seconds.setValue(2.0)
        dialog.fps.setValue(12.0)
        dialog.render_now.setChecked(False)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(TurntableDialog, "exec", accept)
    window.animations.turntable()
    assert (tab.timeline.start, tab.timeline.end, tab.timeline.fps) == (0, 23, 12.0)
    assert len(tab.timeline.track("camera:eye.x").keys) == 24  # type: ignore[union-attr]
    assert window.timeline_panel.end.value() == 23


def test_camera_path_through_saved_views(window: MainWindow, monkeypatch: pytest.MonkeyPatch) -> None:
    tab = window.docs.new_script()
    monkeypatch.setattr(QInputDialog, "getInt", lambda *a, **k: (30, True))
    window.animations.camera_path()  # no saved views: explained, nothing keyed
    assert tab.timeline.tracks == ()
    tab.bookmarks = {"a": Camera((0.0, 0.0, 10.0), (0.0, 0.0, 0.0)), "b": Camera((10.0, 0.0, 0.0), (0.0, 0.0, 0.0))}
    window.animations.camera_path()
    assert (tab.timeline.start, tab.timeline.end) == (0, 30) and tab.timeline.track("camera:eye.x") is not None
