"""Multiple cursors (docs/12 §2.1)."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QTextCursor
from pytestqt.qtbot import QtBot

from structura.themes.loader import load_theme
from structura.ui.editor.code_editor import CodeEditor


@pytest.fixture
def editor(qtbot: QtBot) -> CodeEditor:
    e = CodeEditor(load_theme("structura-dark"))
    qtbot.addWidget(e)
    e.resize(600, 300)
    e.show()
    return e


def _at(editor: CodeEditor, position: int) -> None:
    cursor = editor.textCursor()
    cursor.setPosition(position)
    editor.setTextCursor(cursor)


def test_ctrl_d_selects_occurrences_and_each_keystroke_is_one_undo_step(qtbot: QtBot, editor: CodeEditor) -> None:
    editor.setPlainText("box\nsphere\nbox\nbox\n")
    _at(editor, 1)
    for _ in range(2):  # the word under the cursor, then its next occurrence
        qtbot.keyClick(editor, Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier)
    assert len(editor.multi.cursors()) == 2
    qtbot.keyClicks(editor, "dot")
    assert editor.toPlainText() == "dot\nsphere\ndot\nbox\n"
    editor.undo()  # one keystroke at every cursor is one undo step
    assert editor.toPlainText() == "do\nsphere\ndo\nbox\n"
    editor.undo()
    editor.undo()  # the first keystroke replaced the selections: undoing it brings the words back
    assert editor.toPlainText() == "box\nsphere\nbox\nbox\n"


def test_select_all_occurrences(qtbot: QtBot, editor: CodeEditor) -> None:
    editor.setPlainText("box box\nbox\n")
    _at(editor, 0)
    qtbot.keyClick(editor, Qt.Key.Key_L, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
    qtbot.keyClicks(editor, "grid")
    assert editor.toPlainText() == "grid grid\ngrid\n"


def test_alt_click_adds_carets_and_escape_clears(qtbot: QtBot, editor: CodeEditor) -> None:
    editor.setPlainText("aaa\nbbb\nccc\n")
    _at(editor, 0)
    second = editor.cursorRect(QTextCursor(editor.document().findBlockByNumber(2))).center()
    qtbot.mouseClick(editor.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.AltModifier, second)
    qtbot.keyClicks(editor, "> ")
    assert editor.toPlainText() == "> aaa\nbbb\n> ccc\n"
    qtbot.keyClick(editor, Qt.Key.Key_Escape)
    assert not editor.multi.active


def test_alt_click_on_a_number_adds_a_caret_without_an_undo_step(qtbot: QtBot, editor: CodeEditor) -> None:
    editor.setPlainText("{ x 12 } box\n")
    editor.document().clearUndoRedoStacks()
    _at(editor, 0)
    cursor = QTextCursor(editor.document())
    cursor.setPosition(4)
    point = editor.cursorRect(cursor).center() + QPoint(2, 0)
    qtbot.mouseClick(editor.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.AltModifier, point)
    assert editor.multi.active and not editor.document().isUndoAvailable()


def test_column_selection_makes_one_cursor_per_line(editor: CodeEditor) -> None:
    editor.setPlainText("  box\n  box\n  box\n")
    editor.multi.column_select(2, 12 + 2)  # column 2 on line 1 to column 2 on line 3
    assert len(editor.multi.cursors()) == 3
    editor.multi._edit(lambda c: c.insertText("// "))
    assert editor.toPlainText() == "  // box\n  // box\n  // box\n"
