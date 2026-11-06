"""Keymaps and the keymap editor (docs/14 §4.2)."""

from __future__ import annotations

from pytestqt.qtbot import QtBot

from structura.ui.app_window import MainWindow
from structura.ui.commands.keymap import presets
from structura.ui.dialogs.keymap_editor import KeymapEditor


def test_presets_only_name_existing_commands(window: MainWindow) -> None:
    ids = {c.id for c in window.registry.commands()}
    for name, table in presets().items():
        assert set(table) <= ids, f"{name}: {set(table) - ids}"


def test_default_keymap_has_no_conflicts(window: MainWindow) -> None:
    for preset in presets():
        assert window.keymap.conflicts(window.keymap.effective(preset, {})) == {}, preset


def test_legacy_preset_restores_ctrl_f_for_full_screen(window: MainWindow) -> None:
    window.keymap.save("legacy", {})
    assert window.registry.action("view.fullscreen").shortcut().toString() == "Ctrl+F"
    assert window.registry.action("edit.find").shortcut().toString() == ""
    window.keymap.save("structura", {})
    assert window.registry.action("edit.find").shortcut().toString() == "Ctrl+F"


def test_editor_stores_only_differences_and_shows_conflicts(qtbot: QtBot, window: MainWindow) -> None:
    editor = KeymapEditor(window.keymap, window)
    qtbot.addWidget(editor)
    editor.set_binding("build.run", "Ctrl+F")  # clashes with Find
    assert editor.own == {"build.run": "Ctrl+F"} and "Ctrl+F" in window.keymap.conflicts(editor.bindings())
    assert "1 conflicting" in editor.conflicts.text()
    editor.set_binding("build.run", "F5")  # back to the default: nothing stored
    assert editor.own == {}
    editor.set_binding("render.start", "Ctrl+Alt+9")
    editor.accept()
    assert window.registry.action("render.start").shortcut().toString() == "Ctrl+Alt+9"
    assert window.keymap.overrides() == {"render.start": "Ctrl+Alt+9"}
