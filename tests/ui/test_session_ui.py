"""Session restore, hot exit, crash recovery, encodings, file drops and split view (docs/12 §2.1)."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QTextCursor
from PySide6.QtWidgets import QApplication, QMessageBox
from pytestqt.qtbot import QtBot

from structura.core.lang.diagnostics import Diagnostic, Severity
from structura.core.lang.source import Span
from structura.services.settings import SettingsService
from structura.ui.app_window import MainWindow

SCRIPT = "set maxdepth 9\nrule r {\n  { x 1 } r\n  box\n}\nr\n"


def _window(qtbot: QtBot, tmp_path: Path) -> MainWindow:
    w = MainWindow(SettingsService(tmp_path / "settings.ini"))
    qtbot.addWidget(w, before_close_func=lambda win: None)
    return w


def test_hot_exit_restores_unsaved_text_seed_cursor_and_folds(qtbot: QtBot, tmp_path: Path, window: MainWindow) -> None:
    (tmp_path / "saved.es").write_text("box\n")
    window.docs.open_file(tmp_path / "saved.es")
    tab = window.docs.new_script()
    tab.editor.setPlainText(SCRIPT)
    tab.seed = 7
    tab.editor.go_to(SCRIPT.index("box"))
    tab.editor.folding.refresh()
    tab.editor.folding.toggle(1)
    assert window.session.shutdown()  # what closing the window does: no prompt with hot exit
    again = _window(qtbot, tmp_path)
    again.start([])
    titles = [t.title for t in again.tabs.tabs()]
    assert titles == ["saved.es", "Untitled ●"]
    restored = again.tabs.tabs()[1]
    assert restored.text() == SCRIPT and restored.seed == 7 and restored.modified
    assert restored.editor.folding.folded_lines() == {1}
    assert again.tabs.currentIndex() == 1


def test_without_hot_exit_only_saved_files_are_reopened(qtbot: QtBot, tmp_path: Path, window: MainWindow) -> None:
    window.settings.set_value("general/hot_exit", False)
    (tmp_path / "a.es").write_text("box\n")
    window.docs.open_file(tmp_path / "a.es")
    untitled = window.docs.new_script()
    untitled.editor.document().setModified(False)  # nothing to ask about
    assert window.session.shutdown()
    again = _window(qtbot, tmp_path)
    again.start([])
    assert [t.title for t in again.tabs.tabs()] == ["a.es"]


@pytest.mark.parametrize("accept", [True, False])
def test_a_crash_offers_recovery(qtbot: QtBot, tmp_path: Path, window: MainWindow, monkeypatch: pytest.MonkeyPatch,
                                 accept: bool) -> None:  # fmt: skip
    window.session.guard.start()  # what start-up does: the running lock
    tab = window.docs.new_script()
    tab.editor.setPlainText("// unsaved work\nbox\n")
    window.session.autosave()  # the periodic snapshot; then the process "crashes" (no shutdown, the lock stays)
    assert window.session.recovery.exists()
    answer = QMessageBox.StandardButton.Yes if accept else QMessageBox.StandardButton.No
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: answer)
    again = _window(qtbot, tmp_path)
    again.start([])
    texts = [t.text() for t in again.tabs.tabs()]
    assert ("// unsaved work\nbox\n" in texts) == accept
    assert not again.session.recovery.exists()
    assert (tmp_path / "recovery-declined.json").exists() != accept


def test_a_crash_restores_saved_tabs_parameters_and_camera_too(
    qtbot: QtBot, tmp_path: Path, window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    from structura.core.scene.camera import Camera  # noqa: PLC0415
    from structura.core.scene.lens import Lens  # noqa: PLC0415

    window.session.guard.start()
    (tmp_path / "kept.es").write_text("#define size 2 (float:1-4)\n{ s size } box\n")
    tab = window.docs.open_file(tmp_path / "kept.es")
    tab.params = {"size": 3.5}
    tab.render_overrides = {"max_bounces": 9}
    tab.bookmarks = {"hero": Camera((1.0, 2.0, 3.0), (0.0, 0.0, 0.0), lens=Lens(fstop=4.0))}
    window.session.edit_timer.setInterval(10)
    tab.editor.insertPlainText("")  # no edit: the snapshot is written by the timer below
    window.session.edit_timer.start()
    qtbot.waitUntil(window.session.recovery.exists, timeout=5000)  # written shortly after an edit
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    again = _window(qtbot, tmp_path)
    again.start([])
    restored = again.tabs.tabs()[0]
    assert restored.path == tmp_path / "kept.es" and not restored.modified  # a saved tab comes back as the file
    assert restored.params == {"size": 3.5} and restored.render_overrides == {"max_bounces": 9}
    assert restored.bookmarks["hero"].lens.fstop == 4.0 and restored.initial_camera is not None


def test_saving_keeps_a_legacy_files_encoding_and_line_endings(tmp_path: Path, window: MainWindow) -> None:
    path = tmp_path / "legacy.es"
    path.write_bytes("// café\r\nbox\r\n".encode("cp1252"))
    tab = window.docs.open_file(path)
    assert window.status.labels["encoding"].text() == "Windows-1252 · CRLF"
    cursor = tab.editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    cursor.insertText("sphere\n")
    window.docs.save()
    assert path.read_bytes() == "// café\r\nbox\r\nsphere\r\n".encode("cp1252")


def test_dropping_a_file_on_the_editor_opens_it(tmp_path: Path, window: MainWindow) -> None:
    (tmp_path / "drop.es").write_text("box\n")
    tab = window.docs.new_script()
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(tmp_path / "drop.es"))])
    viewport = tab.editor.viewport()
    actions, button, mods = Qt.DropAction.CopyAction, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier
    QApplication.sendEvent(viewport, QDragEnterEvent(QPointF(10, 10), actions, mime, button, mods))
    QApplication.sendEvent(viewport, QDropEvent(QPointF(10, 10), actions, mime, button, mods))
    assert [t.title for t in window.tabs.tabs()][-1] == "drop.es"
    assert "drop.es" not in tab.text()


def test_split_view_shares_the_document_not_the_cursor(window: MainWindow) -> None:
    tab = window.docs.new_script()
    window.registry.trigger("view.split")
    assert tab.secondary is not None and len(tab.views()) == 2
    second = tab.secondary
    cursor = second.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    cursor.insertText("// from the second view\n")
    second.setTextCursor(cursor)
    assert tab.text().endswith("// from the second view\n")
    assert tab.editor.textCursor().position() != second.textCursor().position()
    tab.editor.set_diagnostics([Diagnostic("E001", Severity.ERROR, "boom", Span(0, 3))])
    assert second.diagnostics and second.gutter.markers
    window.registry.trigger("view.split")
    assert tab.secondary is None and tab.editor.mirrors == []


def test_window_layout_is_restored(qtbot: QtBot, tmp_path: Path, window: MainWindow) -> None:
    window.docks["Console"].hide()
    assert window.session.shutdown()
    again = _window(qtbot, tmp_path)
    again.start([])
    again.show()
    assert not again.docks["Console"].isVisible()
