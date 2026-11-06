"""Editor typing aids and commands (docs/12 §2.1)."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from pytestqt.qtbot import QtBot

from structura.core.lang.analysis import analyze
from structura.themes.loader import load_theme
from structura.ui.editor import editing
from structura.ui.editor.code_editor import CodeEditor
from structura.ui.editor.find_bar import FindBar
from structura.ui.editor.signature import SignatureHelp
from structura.ui.editor.snippet_session import insert_snippet


@pytest.fixture
def editor(qtbot: QtBot) -> CodeEditor:
    e = CodeEditor(load_theme("structura-dark"))
    qtbot.addWidget(e)
    return e


def _put(editor: CodeEditor, text: str, position: int) -> None:
    editor.setPlainText(text)
    cursor = editor.textCursor()
    cursor.setPosition(position)
    editor.setTextCursor(cursor)


def test_braces_auto_close_and_type_over(qtbot: QtBot, editor: CodeEditor) -> None:
    _put(editor, "", 0)
    qtbot.keyClicks(editor, "{ x 1 ")
    assert editor.toPlainText() == "{ x 1 }"
    qtbot.keyClicks(editor, "}")
    assert editor.toPlainText() == "{ x 1 }" and editor.textCursor().position() == 7


def test_enter_between_braces_opens_an_indented_block(qtbot: QtBot, editor: CodeEditor) -> None:
    _put(editor, "rule R {}", 8)
    qtbot.keyClick(editor, Qt.Key.Key_Return)
    assert editor.toPlainText() == "rule R {\n  \n}"
    assert editor.textCursor().blockNumber() == 1


def test_toggle_comment_round_trips(editor: CodeEditor) -> None:
    _put(editor, "box\n  sphere\n", 0)
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
    editor.setTextCursor(cursor)
    editing.toggle_comment(editor)
    assert editor.toPlainText() == "// box\n  // sphere\n"
    editing.toggle_comment(editor)
    assert editor.toPlainText() == "box\n  sphere\n"


def test_line_operations(editor: CodeEditor) -> None:
    _put(editor, "a\nb\nc", 0)
    editing.move_line(editor, down=True)
    assert editor.toPlainText() == "b\na\nc"
    editing.duplicate_line(editor)
    assert editor.toPlainText() == "b\na\na\nc"
    editing.delete_line(editor)
    assert editor.toPlainText().count("a") == 1


def test_find_and_replace_all_is_one_undo_step(editor: CodeEditor) -> None:
    _put(editor, "box box sphere box", 0)
    bar = FindBar(editor)
    bar.open()
    bar.find_edit.setText("box")
    assert bar.count.text() == "3 matches"
    bar.replace_edit.setText("grid")
    bar.replace_all()
    assert editor.toPlainText() == "grid grid sphere grid"
    editor.undo()
    assert editor.toPlainText() == "box box sphere box"


def test_bracket_matching_highlights_both_ends(editor: CodeEditor) -> None:
    _put(editor, "{ x { y } }", 1)
    spans = [(s.cursor.selectionStart(), s.cursor.selectionEnd()) for s in editor._selections["brackets"]]
    assert sorted(spans) == [(0, 1), (10, 11)]


def test_alt_drag_scrubs_numbers_in_one_undo_step(editor: CodeEditor) -> None:
    _put(editor, "{ x 1.50 rz 10 } box", 0)
    scrub = editor.scrubber
    assert scrub.begin(5, 100.0)  # inside "1.50"
    scrub.move(100.0 + 4 * 3, Qt.KeyboardModifier.NoModifier)  # three steps of 0.01
    assert editor.toPlainText() == "{ x 1.53 rz 10 } box"
    scrub.move(100.0 + 4 * 3, Qt.KeyboardModifier.ControlModifier)  # coarse: ten times larger steps
    assert editor.toPlainText() == "{ x 1.80 rz 10 } box"
    scrub.end()
    assert scrub.begin(13, 0.0)  # the integer 10 stays an integer
    scrub.move(-8.0, Qt.KeyboardModifier.NoModifier)
    scrub.end()
    assert editor.toPlainText() == "{ x 1.80 rz 8 } box"
    editor.undo()
    assert editor.toPlainText() == "{ x 1.80 rz 10 } box"


def test_semantic_layer_marks_undefined_and_unused_rules(editor: CodeEditor) -> None:
    _put(editor, "R\nrule R { Q }\nrule S { box }", 0)
    hl = editor.highlighter
    hl.set_symbols(frozenset({"r", "s"}), frozenset({"s"}))
    assert hl._semantic("rule.ref", "Q") == "rule.undefined"
    assert hl._semantic("rule.ref", "R") == "rule.ref"
    assert hl._semantic("rule.def", "S") == "rule.unused"
    hl.set_symbols(None, frozenset())
    assert hl._semantic("rule.ref", "Q") == "rule.ref"


def test_colour_literals_parse_for_swatches() -> None:
    from structura.ui.editor.swatches import color_of  # noqa: PLC0415

    assert color_of("#f80").name() == "#ff8800"
    assert color_of("red").name() == "#ff0000"
    assert color_of("notacolour") is None


def test_typing_opens_completions_and_enter_accepts(qtbot: QtBot) -> None:
    from structura.ui.editor.completion import CompletionController  # noqa: PLC0415

    editor = CodeEditor(load_theme("nord"))
    qtbot.addWidget(editor)
    completion = CompletionController(editor)
    editor.show()
    qtbot.keyClicks(editor, "set max")
    assert completion.popup.isVisible()
    assert [i.label for i in completion.popup.items] == ["maxdepth", "maxobjects", "maxsize"]
    qtbot.keyClick(editor, Qt.Key.Key_Down)
    qtbot.keyClick(editor, Qt.Key.Key_Return)
    assert editor.toPlainText() == "set maxobjects" and not completion.popup.isVisible()


def test_inlay_hints_show_probabilities_loop_counts_and_materials() -> None:
    text = "R\nrule R w 3 { box }\nrule R w 1 { sphere }\n3 * { x 1 } 4 * { y 1 } box\n"
    assert [h.text for h in analyze(text).hints if h.kind == "probability"] == ["⟶ 75.0%", "⟶ 25.0%"]
    assert [h.text for h in analyze(text).hints if h.kind == "loops"] == ["×12 (3 × 4)"]
    v2 = "#version 2\nmaterial shiny { roughness 0.1 }\nbox::shiny\nbox::gold\n"
    assert [h.text for h in analyze(v2).hints] == ["◆ shiny", "◆ gold (preset)"]


def test_signature_help_appears_in_calls_and_hides_after(qtbot: QtBot, editor: CodeEditor) -> None:
    help_ = SignatureHelp(editor)
    editor.show()
    _put(editor, "{ x (mix(1, ", 12)
    help_.refresh()
    assert help_.label.isVisible() and "<b>t</b>" not in help_.label.text() and "<b>b</b>" in help_.label.text()
    _put(editor, "{ x (mix(1, 2, 3)) } box", 24)
    help_.refresh()
    assert not help_.label.isVisible()


def test_signature_help_follows_typing(qtbot: QtBot, editor: CodeEditor) -> None:
    help_ = SignatureHelp(editor)
    editor.show()
    _put(editor, "{ x ", 4)
    qtbot.keyClicks(editor, "(pow(2,")
    qtbot.waitUntil(lambda: help_.label.isVisible() and "<b>exponent</b>" in help_.label.text(), timeout=2000)


def test_snippet_session_visits_stops_and_mirrors(qtbot: QtBot, editor: CodeEditor) -> None:
    editor.setPlainText("")
    insert_snippet(editor, "rule ${1:spiral} {\n  { x ${2:1} } ${1:spiral}\n}$0")
    assert editor.textCursor().selectedText() == "spiral"
    qtbot.keyClicks(editor, "coil")  # replaces the selected placeholder
    qtbot.keyClick(editor, Qt.Key.Key_Tab)
    assert editor.toPlainText() == "rule coil {\n  { x 1 } coil\n}"  # the mirror followed
    assert editor.textCursor().selectedText() == "1"
    qtbot.keyClick(editor, Qt.Key.Key_Tab)  # to $0: the session ends at the final position
    assert not editor.snippets.active and editor.textCursor().position() == len(editor.toPlainText())
