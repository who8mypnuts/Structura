"""Folding, block comments, rainbow brackets and view options of the code editor (docs/12 §2.1)."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QTextCursor, QTextOption
from PySide6.QtWidgets import QPlainTextEdit, QWidget
from pytestqt.qtbot import QtBot

from structura.core.lang.analysis import analyze
from structura.themes.loader import load_theme
from structura.ui.app_window import MainWindow
from structura.ui.commands.registry import Command, CommandRegistry
from structura.ui.editor import editing, quick_fix
from structura.ui.editor.code_editor import CodeEditor
from structura.ui.editor.highlighter import brace_depth
from structura.ui.editor.options import EditorOptions
from structura.ui.editor.peek import PeekPopup, peek_definition
from structura.ui.editor.quick_fix import apply_fix, fixes_at, show_quick_fixes, show_refactorings
from structura.ui.fonts import CODE_FAMILY

SCRIPT = "set maxdepth 9\nrule r {\n  { x 1 } r\n  box\n}\nr\n"


@pytest.fixture
def editor(qtbot: QtBot) -> CodeEditor:
    e = CodeEditor(load_theme("structura-dark"))
    qtbot.addWidget(e)
    e.setPlainText(SCRIPT)
    e.folding.refresh()
    return e


def _visible(editor: CodeEditor) -> list[bool]:
    doc = editor.document()
    return [doc.findBlockByNumber(n).isVisible() for n in range(doc.blockCount())]


def test_toggle_folds_the_rule_body_and_go_to_reveals_it(editor: CodeEditor) -> None:
    editor.folding.toggle(1)
    assert _visible(editor)[:6] == [True, True, False, False, False, True]
    editor.go_to(SCRIPT.index("box"))
    assert all(_visible(editor))


def test_a_fold_follows_edits_above_it(editor: CodeEditor) -> None:
    editor.folding.toggle(1)
    cursor = QTextCursor(editor.document())
    cursor.insertText("// new first line\n")
    editor.folding.refresh()
    assert editor.folding.folded_lines() == {2}
    assert _visible(editor)[:7] == [True, True, True, False, False, False, True]


def test_fold_all_and_unfold_all(editor: CodeEditor) -> None:
    editor.folding.fold_all()
    assert not all(_visible(editor))
    editor.folding.unfold_all()
    assert all(_visible(editor))


def test_fold_at_uses_the_innermost_range_around_the_cursor(editor: CodeEditor) -> None:
    editor.folding.fold_at(3, True)  # inside the rule body
    assert editor.folding.folded_lines() == {1} and editor.textCursor().blockNumber() == 1
    editor.folding.fold_at(1, False)
    assert editor.folding.folded_lines() == set()


def test_block_comment_round_trips(editor: CodeEditor) -> None:
    cursor = editor.textCursor()
    cursor.setPosition(SCRIPT.index("box"))
    editor.setTextCursor(cursor)
    editing.toggle_block_comment(editor)
    assert "  /* box */" in editor.toPlainText()
    editing.toggle_block_comment(editor)
    assert editor.toPlainText() == SCRIPT


def test_rainbow_brackets_track_depth_across_lines(editor: CodeEditor) -> None:
    editor.set_options(EditorOptions(rainbow_brackets=True))
    doc = editor.document()
    depths = [brace_depth(doc.findBlockByNumber(n).userState()) for n in range(5)]
    assert depths == [0, 1, 1, 1, 0]  # after each line: 'rule r {' opens, '}' closes
    formats = doc.findBlockByNumber(2).layout().formats()
    colours = {f.format.foreground().color().name() for f in formats if f.length == 1}
    assert len(colours) >= 2  # the inner { } differ from the rule's braces


def test_view_options_apply_wrap_and_whitespace(editor: CodeEditor) -> None:
    editor.set_options(EditorOptions(word_wrap=True, show_whitespace=True, code_size=14))
    assert editor.lineWrapMode() == QPlainTextEdit.LineWrapMode.WidgetWidth
    assert editor.document().defaultTextOption().flags() & QTextOption.Flag.ShowTabsAndSpaces
    assert editor.font().pointSize() == 14
    editor.set_options(EditorOptions())
    assert editor.lineWrapMode() == QPlainTextEdit.LineWrapMode.NoWrap
    assert not editor.document().defaultTextOption().flags() & QTextOption.Flag.ShowTabsAndSpaces


def test_view_toggles_persist_and_reach_every_tab(window: MainWindow) -> None:
    first, second = window.docs.new_script(), window.docs.new_script()
    window.registry.trigger("view.word_wrap")
    assert window.editor_actions.options().word_wrap
    assert all(t.editor.lineWrapMode() == QPlainTextEdit.LineWrapMode.WidgetWidth for t in (first, second))
    assert window.registry.action("view.word_wrap").isChecked()


def test_unparsable_shortcuts_are_rejected(qtbot: QtBot) -> None:
    host = QWidget()
    qtbot.addWidget(host)
    registry = CommandRegistry(host)
    with pytest.raises(ValueError, match="unparsable shortcut"):
        registry.register(Command("x.y", "X", lambda: None, "Ctrl+K Ctrl+T"))


def test_code_font_and_zoom_survive_the_application_style_sheet(window: MainWindow) -> None:
    tab = window.docs.new_script()
    assert tab.editor.fontInfo().family() == CODE_FAMILY  # the app QSS sets the UI font on every QWidget
    tab.editor.zoom(4)
    size = tab.editor.fontInfo().pointSize()
    window.dialogs.toggle_theme()  # re-applies the application style sheet
    assert tab.editor.fontInfo().family() == CODE_FAMILY and tab.editor.fontInfo().pointSize() == size


def test_quick_fix_at_the_cursor_is_one_undo_step(editor: CodeEditor) -> None:
    text = "set rng old\nset maxdepth 9\nr\nrule r { { x 1 } missing }\n"
    editor.setPlainText(text)
    editor.set_diagnostics(list(analyze(text).diagnostics))
    position = text.index("missing") + 2
    fixes = fixes_at(editor, position)
    assert [f.title for f in fixes] == ["Create rule 'missing'"]
    apply_fix(editor, fixes[0])
    assert editor.toPlainText().endswith("rule missing {\n  box\n}\n")
    editor.undo()
    assert editor.toPlainText() == text
    assert [f.title for f in fixes_at(editor, 2)] == ["Remove 'set rng old'"]  # same line, no span overlap needed


def test_the_refactor_menu_offers_and_applies_refactorings(editor: CodeEditor, monkeypatch: pytest.MonkeyPatch) -> None:
    shown: list[list[str]] = []
    monkeypatch.setattr(quick_fix, "run_menu", lambda menu, _point: shown.append([a.text() for a in menu.actions()]))
    text = "{ x 1 } box\n"
    editor.setPlainText(text)
    cursor = editor.textCursor()
    cursor.setPosition(2)
    editor.setTextCursor(cursor)
    show_refactorings(editor)
    assert shown[-1][0].startswith("Extract") and "Convert to '1 * { … }'" in shown[-1]
    show_quick_fixes(editor)  # Ctrl+. lists them too (no problems here)
    assert shown[-1] == shown[-2]


def test_f1_peek_and_breadcrumbs(window: MainWindow) -> None:
    tab = window.docs.new_script()
    text = "set maxdepth 9\nr\nrule r { { rx 10 } r box }\nrule r w 2 { sphere }\n"
    tab.editor.setPlainText(text)
    tab.editor.set_analysis(analyze(text))
    tab.editor.go_to(text.index("rx") + 1)
    assert window.help.anchor_at_cursor() == "op-rx"
    window.registry.trigger("help.reference")
    assert window.help.browser is not None and window.help.browser.isVisible()
    window.help.browser.close()
    assert tab.breadcrumbs.rule.text() == "rule r"
    tab.editor.go_to(0)
    assert tab.breadcrumbs.rule.text() == "top level"
    tab.editor.go_to(text.index("r\nrule"))
    assert peek_definition(tab.editor, "r")
    popup = tab.editor.findChild(PeekPopup)
    assert popup is not None and "sphere" in popup.view.toPlainText() and "{ rx 10 }" in popup.view.toPlainText()
    popup.close()


def test_sticky_header_pins_the_enclosing_rule(qtbot: QtBot, editor: CodeEditor) -> None:
    body = "\n".join(f"  {{ x {i} }} box" for i in range(60))
    editor.setPlainText(f"set maxdepth 9\nrule long {{\n{body}\n}}\nlong\n")
    editor.resize(500, 200)
    editor.show()
    editor.folding.refresh()
    editor.verticalScrollBar().setValue(20)
    qtbot.waitUntil(editor.sticky.isVisible, timeout=2000)
    assert editor.sticky.headers == [1]  # 'rule long {'
    editor.verticalScrollBar().setValue(0)
    assert not editor.sticky.isVisible()


def test_minimap_skips_folded_lines_and_scrolls_on_click(qtbot: QtBot, editor: CodeEditor) -> None:
    body = "\n".join(f"  {{ x {i} }} box" for i in range(200))
    editor.setPlainText(f"set maxdepth 9\nrule long {{\n{body}\n}}\nlong\n")
    editor.resize(500, 300)
    editor.show()
    editor.minimap.rebuild()
    assert len(editor.minimap.lines) == editor.blockCount()
    editor.folding.refresh()
    editor.folding.toggle(1)
    assert len(editor.minimap.lines) == editor.blockCount() - 201  # the folded body is not drawn
    editor.folding.unfold_all()
    qtbot.mouseClick(editor.minimap, Qt.MouseButton.LeftButton, pos=editor.minimap.rect().bottomLeft() - QPoint(-5, 5))
    assert editor.verticalScrollBar().value() > 0


def test_provenance_hover_finds_the_instances_of_a_call(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    text = "set maxdepth 3\n4 * { x 1 } box\n{ y 2 } sphere\n"
    tab.editor.setPlainText(text)

    def built() -> bool:
        a = tab.analysis
        return tab.outcome is not None and a is not None and a.version == tab.version and a.digest == tab.built_digest

    qtbot.waitUntil(built, timeout=20000)
    action, rows = window.provenance.rows_for(tab, text.index("box") + 1)
    assert action is not None and len(rows) == 4
    _, sphere = window.provenance.rows_for(tab, text.index("sphere") + 1)
    assert len(sphere) == 1 and set(sphere).isdisjoint(rows)
    QTextCursor(tab.editor.document()).insertText("// shifted\n")  # positions moved: nothing until re-analysed
    assert len(window.provenance.rows_for(tab, text.index("box") + 1)[1]) == 0
    qtbot.waitUntil(built, timeout=20000)
    assert len(window.provenance.rows_for(tab, text.index("box") + len("// shifted\n") + 1)[1]) == 4


def test_inline_parameter_sliders_mirror_the_panel(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("#define angle 20 (float:0-90)\nset maxdepth 5\n{ rz angle } box\n")
    qtbot.waitUntil(lambda: len(tab.editor.inline_params.sliders) == 1, timeout=20000)
    inline = tab.editor.inline_params.sliders[0]
    assert inline.param.name == "angle" and inline.isVisible()
    inline.slider.setValue(inline._to_slider(45.0))  # drag the inline slider
    assert tab.params["angle"] == pytest.approx(45.0, abs=0.1)
    panel = window.parameters.findChildren(type(inline))[0]
    assert panel.value == pytest.approx(45.0, abs=0.1)
    panel.spin.setValue(10.0)  # and the other way round
    assert inline.value == pytest.approx(10.0, abs=0.1)


def test_hovering_a_rule_previews_it_built_alone(
    qtbot: QtBot, window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from structura.ui import rule_previews  # noqa: PLC0415

    monkeypatch.setattr(rule_previews, "cache_dir", lambda: tmp_path)
    tab = window.docs.new_script()
    tab.editor.setPlainText("R\nrule R { box { x 1.2 } sphere }\n")
    qtbot.waitUntil(lambda: tab.analysis is not None and tab.analysis.ok, timeout=30000)
    assert tab.editor.rule_preview is not None and tab.editor.rule_preview("R") is None  # being made
    with qtbot.waitSignal(window.editor_actions.previews.ready, timeout=60000) as ready:
        pass
    assert ready.args == ["R"]
    path = tab.editor.rule_preview("R")
    assert path is not None and path.parent == tmp_path and path.stat().st_size > 0
    tab.completion.hovered_rule = "R"
    assert path.as_posix() in tab.completion._preview()
