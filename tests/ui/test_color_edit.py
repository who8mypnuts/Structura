"""Picking colours in the editor (docs/12 §2.3): literal detection, format preservation, live preview."""

from __future__ import annotations

import pytest
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog, QMenu
from pytestqt.qtbot import QtBot

from structura.themes.loader import load_theme
from structura.ui.app_window import MainWindow
from structura.ui.editor.code_editor import CodeEditor
from structura.ui.editor.color_edit import ColorEdit, color_token_at, format_like


@pytest.fixture
def editor(qtbot: QtBot) -> CodeEditor:
    e = CodeEditor(load_theme("nord"))
    qtbot.addWidget(e)
    return e


@pytest.mark.parametrize(
    ("original", "chosen", "expected"),
    [("#f80", "#ff8800", "#f80"), ("#f80", "#ff8801", "#ff8801"), ("#FF8800", "#112233", "#112233".upper()),
     ("#abcdef", "#ffffff", "#ffffff"), ("red", "#0000ff", "blue"), ("Red", "#00ff00", "Lime"),
     ("red", "#123456", "#123456"), ("", "#102030", "#102030")],
)  # fmt: skip
def test_the_new_value_keeps_the_literal_style(original: str, chosen: str, expected: str) -> None:
    assert format_like(original, QColor(chosen)) == expected


def test_colour_literals_are_found_under_the_cursor(editor: CodeEditor) -> None:
    text = "#define warm #f80\n{ color red } box\n{ color random x 1 } box\nset background #FFFFFF\n"
    editor.setPlainText(text)
    assert color_token_at(editor, text.index("#f80") + 2) == (text.index("#f80"), "#f80")  # in a #define
    assert color_token_at(editor, text.index("red") + 1) == (text.index("red"), "red")
    assert color_token_at(editor, text.index("random") + 1) is None  # a keyword, not a colour
    assert color_token_at(editor, text.index("box")) is None
    assert color_token_at(editor, text.index("#FFFFFF")) == (text.index("#FFFFFF"), "#FFFFFF")


def test_the_script_follows_the_picker_and_cancel_restores_it(editor: CodeEditor) -> None:
    editor.setPlainText("{ color #f80 } box")
    session = ColorEdit(editor, 8, "#f80")
    session.dialog.setCurrentColor(QColor("#00ff00"))
    assert editor.toPlainText() == "{ color #0f0 } box"  # live preview, in the literal's style
    session.dialog.setCurrentColor(QColor("#123456"))
    assert editor.toPlainText() == "{ color #123456 } box"
    session._finished(QColorDialog.DialogCode.Rejected)
    assert editor.toPlainText() == "{ color #f80 } box"


def test_accepting_is_one_undo_step(editor: CodeEditor) -> None:
    editor.setPlainText("{ color red } box")
    session = ColorEdit(editor, 8, "red")
    for name in ("#00ff00", "#0000ff", "#ffff00"):
        session.dialog.setCurrentColor(QColor(name))
    session.dialog.setCurrentColor(QColor("#0000ff"))
    session.dialog.done(QColorDialog.DialogCode.Accepted)
    assert editor.toPlainText() == "{ color blue } box"
    editor.document().undo()
    assert editor.toPlainText() == "{ color red } box"


def test_insert_colour_at_the_cursor(editor: CodeEditor) -> None:
    editor.setPlainText("{ color  } box")
    session = ColorEdit(editor, 8, "")
    session.dialog.setCurrentColor(QColor("#336699"))
    session.dialog.done(QColorDialog.DialogCode.Accepted)
    assert editor.toPlainText() == "{ color #336699 } box"


def test_the_context_menu_offers_the_language_commands(window: MainWindow) -> None:
    tab = window.docs.new_script()
    assert tab.editor.menu_extender is not None  # the window installs it on every editor
    menu = QMenu()
    tab.editor.menu_extender(menu, menu.addAction("Undo"))
    names = [a.objectName() for a in menu.actions()]
    assert names[-1] == "" and {"edit.definition", "edit.rename", "edit.quick_fix"} <= set(names)
    menu.deleteLater()
