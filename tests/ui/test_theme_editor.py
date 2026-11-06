"""The theme editor dialog (docs/13 §8)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from structura.themes import authoring, loader
from structura.ui.app_window import MainWindow
from structura.ui.dialogs.theme_editor import ThemeEditor


@pytest.fixture(autouse=True)
def user_themes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "themes"
    monkeypatch.setattr(loader, "user_dir", lambda: folder)
    monkeypatch.setattr(authoring, "user_dir", lambda: folder)
    return folder


@pytest.mark.allow_stalls  # restyling every widget for a theme preview is one deliberate, user-initiated stall
def test_edits_preview_live_and_cancel_reverts(qtbot: QtBot, window: MainWindow) -> None:
    original = window.themes.theme
    editor = ThemeEditor(window.themes, window)
    qtbot.addWidget(editor)
    seen: list[object] = []
    window.themes.theme_changed.connect(seen.append)
    editor.draft.set_role("ui.accent", "#FF00AA")
    editor._refresh()
    qtbot.waitUntil(lambda: any(getattr(t, "colors", {}).get("ui.accent") == "#FF00AA" for t in seen), timeout=2000)
    editor.reject()
    assert window.themes.theme is original and seen[-1] is original


@pytest.mark.allow_stalls
def test_saving_an_edited_builtin_creates_a_user_copy(qtbot: QtBot, window: MainWindow, user_themes: Path) -> None:
    editor = ThemeEditor(window.themes, window)
    qtbot.addWidget(editor)
    assert editor.draft.read_only  # structura-dark is built in
    editor.draft.set_role("syntax.keyword", "#FF7A00")
    editor.save()
    saved = list(user_themes.glob("*.toml"))
    assert len(saved) == 1 and window.themes.theme.meta.id == saved[0].stem
    assert window.themes.theme["syntax.keyword"] == "#FF7A00"
