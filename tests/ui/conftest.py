"""UI test fixtures: an isolated MainWindow (temporary settings) on the offscreen platform."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from structura.services.settings import SettingsService
from structura.ui.app_window import MainWindow
from structura.ui.fonts import register_fonts


@pytest.fixture
def window(
    qtbot: QtBot, tmp_path: Path, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> Iterator[MainWindow]:
    if "preview" not in request.node.name:
        monkeypatch.setenv("STRUCTURA_PREVIEW", "off")  # keep the CPU renderer out of unrelated tests
    register_fonts()
    w = MainWindow(SettingsService(tmp_path / "settings.ini"))
    qtbot.addWidget(w, before_close_func=_discard_edits)  # no "unsaved changes" dialog at teardown
    w.show()
    yield w


def _discard_edits(w: MainWindow) -> None:
    for tab in w.tabs.tabs():
        tab.editor.document().setModified(False)
