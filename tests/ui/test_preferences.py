"""Preferences (docs/14 §7): sections, fonts and density, following the system, caches, the memory guard."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from structura.ui import render_actions
from structura.ui.app_window import MainWindow
from structura.ui.dialogs.preferences import CACHES, PreferencesDialog, clear_caches
from structura.ui.fonts import CODE_FAMILY, choose_families, code_family
from structura.ui.settings_actions import followed_theme


def test_the_dialog_has_sections_and_applies_every_value(window: MainWindow) -> None:
    dialog = PreferencesDialog(window.settings, window)
    titles = [dialog.tabs.tabText(i) for i in range(dialog.tabs.count())]
    assert titles == ["General", "Appearance", "Editor", "Viewport", "Rendering", "Paths", "Advanced"]
    values = dialog.values()
    assert {"appearance/density", "render/memory_guard", "advanced/log_level", "editor/code_font"} <= set(values)
    dialog.apply()
    assert window.settings.value("render/memory_guard", 0) == 80


def test_clear_caches_removes_only_the_cache_folders(tmp_path: Path) -> None:
    for name in (*CACHES[:2], "keep"):
        (tmp_path / name).mkdir()
    assert clear_caches(tmp_path) == 2
    assert [p.name for p in tmp_path.iterdir()] == ["keep"]


def test_following_the_system_picks_the_pair_on_a_mismatch() -> None:
    assert followed_theme("structura-dark", False) == "structura-light"
    assert followed_theme("structura-dark", True) == "structura-dark"
    assert followed_theme("structura-dark", None) == "structura-dark"


def test_fonts_density_log_level_and_preset_apply_live(window: MainWindow) -> None:
    choose_families("Inter", "No Such Mono")
    assert code_family() == CODE_FAMILY
    window.settings.set_value("appearance/density", "compact")
    window.settings.set_value("advanced/log_level", "warning")
    window.settings.set_value("render/preset", "Draft")
    window.apply_settings()
    app = QApplication.instance()
    assert isinstance(app, QApplication) and "padding: 2px" in app.styleSheet()
    assert window.render_view.controls.preset.currentText() == "Draft"
    assert logging.getLogger("structura").level == logging.WARNING


def test_the_memory_guard_refuses_a_render_that_does_not_fit(
    qtbot: QtBot, window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("sphere\n")
    qtbot.waitUntil(lambda: tab.outcome is not None, timeout=30000)
    assert window.render_actions.guarded_source() is not None
    monkeypatch.setattr(render_actions, "available_bytes", lambda: 1024)
    assert window.render_actions.guarded_source() is None
    assert "memory guard" in window.status.currentMessage()
