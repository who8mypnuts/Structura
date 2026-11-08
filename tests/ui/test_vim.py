"""Vim keybindings (docs/12 §2.1, P2): motions and parsing (pure), then the modes, operators, registers,
'.', the command line and search on a real editor."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from structura.themes.loader import load_theme
from structura.ui.app_window import MainWindow
from structura.ui.editor import vim_core as core
from structura.ui.editor.code_editor import CodeEditor
from structura.ui.editor.options import EditorOptions
from structura.ui.editor.vim import Mode

TEXT = "rule tree {\n  { x 1 } box\n  sphere\n}\n"


def test_parsing_counts_operators_and_motions() -> None:
    assert core.parse("2d3w") == core.Command(6, "d", "w", True)
    assert core.parse("dd") == core.Command(1, "d", "d")
    assert core.parse("gg") == core.Command(1, "", "gg")
    assert core.parse("fx") == core.Command(1, "", "fx")
    assert core.parse("d") is True and core.parse("2") is True and core.parse("g") is True
    assert core.parse("dy") is None and core.parse("q") is None
    assert core.parse("3x") == core.Command(3, "", "x", True) and core.parse("rz") == core.Command(1, "", "rz")


def test_motions() -> None:
    t = "alpha beta.gamma\n  delta\n\nlast"
    assert core.move(t, 0, "w", 0) == 6 and core.move(t, 6, "w", 0) == 10 and core.move(t, 6, "W", 0) == 19
    assert core.move(t, 6, "e", 0) == 9 and core.move(t, 10, "b", 0) == 6
    assert core.move(t, 3, "$", 0) == 15 and core.move(t, 20, "^", 0) == 19 and core.move(t, 20, "0", 0) == 17
    assert core.move(t, 2, "j", 2) == 19 and core.move(t, 19, "k", 2) == 2
    assert core.move(t, 0, "}", 0) == t.index("\n\n") + 1 and core.move(t, 0, "fa", 0) == 4
    assert core.move(t, 0, "ta", 0) == 3 and core.move(t, 0, ";", 0, "fa") == 4
    assert core.matching_bracket("a { b { c } }", 2) == 12


@pytest.fixture
def editor(qtbot: QtBot) -> CodeEditor:
    e = CodeEditor(load_theme("structura-dark"))
    qtbot.addWidget(e)
    e.setPlainText(TEXT)
    e.set_options(EditorOptions(vim=True))
    e.show()
    return e


def keys(qtbot: QtBot, editor: CodeEditor, text: str) -> None:
    for ch in text:
        if ch == "\x1b":
            qtbot.keyClick(editor, Qt.Key.Key_Escape)
        else:
            qtbot.keyClicks(editor, ch)


def test_normal_mode_commands_edit_and_undo(qtbot: QtBot, editor: CodeEditor) -> None:
    assert editor.vim.mode == Mode.NORMAL and editor.cursorWidth() > 1
    keys(qtbot, editor, "dw")
    assert editor.toPlainText().startswith("tree {")
    keys(qtbot, editor, "u")
    assert editor.toPlainText() == TEXT
    keys(qtbot, editor, "j2ddp")  # two lines into the register, pasted below the line now current
    assert editor.toPlainText() == "rule tree {\n}\n  { x 1 } box\n  sphere\n"
    keys(qtbot, editor, "ggx.")
    assert editor.toPlainText().startswith("le tree")


def test_insert_change_and_repeat(qtbot: QtBot, editor: CodeEditor) -> None:
    keys(qtbot, editor, "cwRULE\x1b")
    assert editor.toPlainText().startswith("RULE tree {") and editor.vim.mode == Mode.NORMAL
    keys(qtbot, editor, "jA // hi\x1b")
    assert "  { x 1 } box // hi\n" in editor.toPlainText()
    keys(qtbot, editor, "j.")
    assert "  sphere // hi\n" in editor.toPlainText()
    keys(qtbot, editor, "ggOstart\x1b")
    assert editor.toPlainText().startswith("start\nRULE")


def test_visual_modes_and_registers(qtbot: QtBot, editor: CodeEditor) -> None:
    keys(qtbot, editor, "jVjy")
    assert editor.vim.register == ("  { x 1 } box\n  sphere\n", True) and editor.vim.mode == Mode.NORMAL
    keys(qtbot, editor, "GP")
    assert editor.toPlainText().endswith("  { x 1 } box\n  sphere\n}\n")
    keys(qtbot, editor, "ggvex")
    assert editor.toPlainText().startswith(" tree {")
    keys(qtbot, editor, "gg~J")
    assert editor.toPlainText().startswith(" Tree { { x 1 } box")  # gg lands on the first non-blank


def test_search_and_the_command_line(qtbot: QtBot, editor: CodeEditor) -> None:
    keys(qtbot, editor, "/")
    assert editor.vim.prompt.isVisible()
    qtbot.keyClicks(editor.vim.prompt, "sphere")
    qtbot.keyClick(editor.vim.prompt, Qt.Key.Key_Return)
    assert editor.textCursor().position() == TEXT.index("sphere") and not editor.vim.prompt.isVisible()
    with qtbot.waitSignal(editor.vim.command_entered) as entered:
        keys(qtbot, editor, ":")
        qtbot.keyClicks(editor.vim.prompt, "w")
        qtbot.keyClick(editor.vim.prompt, Qt.Key.Key_Return)
    assert entered.args == ["w"]
    keys(qtbot, editor, ":")
    qtbot.keyClicks(editor.vim.prompt, "2")
    qtbot.keyClick(editor.vim.prompt, Qt.Key.Key_Return)
    assert editor.textCursor().blockNumber() == 1


def test_turning_vim_off_restores_plain_typing(qtbot: QtBot, editor: CodeEditor) -> None:
    editor.set_options(EditorOptions(vim=False))
    keys(qtbot, editor, "x")
    assert editor.toPlainText().startswith("x") and editor.cursorWidth() == 1


def test_vim_in_the_window_comes_before_completion_and_shows_its_mode(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("box\n")
    window.registry.trigger("view.vim")
    assert tab.editor.vim.enabled and window.status.labels["vim"].text() == "-- NORMAL --"
    tab.editor.setFocus()
    keys(qtbot, tab.editor, "x")  # not typed, not completed: deleted
    assert tab.editor.toPlainText() == "ox\n"
    keys(qtbot, tab.editor, "i")
    assert window.status.labels["vim"].text() == "-- INSERT --"
    window.registry.trigger("view.vim")
    assert window.status.labels["vim"].text() == ""
