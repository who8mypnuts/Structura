"""The Files panel (docs/14 §3)."""

from __future__ import annotations

from pathlib import Path

from pytestqt.qtbot import QtBot

from structura.ui.app_window import MainWindow


def test_files_panel_follows_the_script_and_manages_files(qtbot: QtBot, window: MainWindow, tmp_path: Path) -> None:
    script = tmp_path / "tree.es"
    script.write_text("box\n")
    (tmp_path / "notes.txt").write_text("not shown")
    window.docs.open_file(script)
    files = window.files
    assert files.folder == tmp_path
    qtbot.waitUntil(lambda: files.model.rowCount(files.tree.rootIndex()) == 1, timeout=10000)  # notes.txt hidden
    created = files.new_script(tmp_path, "spiral")
    assert created == tmp_path / "spiral.es" and created.exists()
    assert window.tabs.current() is not None and window.tabs.current().path == created  # opened
    renamed = files.rename(created, "helix.es")
    assert renamed == tmp_path / "helix.es" and not created.exists()
    assert files.delete(tmp_path / "helix.es", confirmed=True) and not (tmp_path / "helix.es").exists()
    files.pinned = True
    window.docs.open_file(Path(__file__))  # a pinned folder stays
    assert files.folder == tmp_path
