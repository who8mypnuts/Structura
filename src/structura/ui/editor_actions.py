"""Editor commands of the main window (docs/12 §2.1): block comments, folding and the view options
(word wrap, whitespace, guides, rainbow brackets, minimap, sticky scroll), applied to every open tab."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QMessageBox

from ..core.lang.convert import convert_to_v2
from .documents import EditorTab
from .editor import editing
from .editor.code_editor import CodeEditor
from .editor.options import EditorOptions, load_options, toggle_option
from .editor.peek import peek_definition
from .editor.quick_fix import show_quick_fixes, show_refactorings
from .i18n import tr
from .rule_previews import RulePreviews

if TYPE_CHECKING:
    from .app_window import MainWindow


class EditorActions(QObject):
    """The editor's commands and the rule previews shown in the editor.

    Comments, quick fixes, refactoring, peek, folding, the split view, options, Vim commands and conversion
    to v2.
    """

    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        window.tabs.tab_added.connect(self._on_tab_added)
        self.previews = RulePreviews(window.runner, self)
        self.previews.ready.connect(self._preview_ready)

    def _with_editor(self, action: Callable[[CodeEditor], object]) -> None:
        tab = self.w.tabs.current()
        if tab is not None:
            action(tab.editor)

    # -- editing -------------------------------------------------------------------------------------------
    def block_comment(self) -> None:
        self._with_editor(editing.toggle_block_comment)

    def standard(self, name: str) -> None:
        """Undo, redo, cut, copy, paste, select all: the editor's own operations (menu entries)."""
        self._with_editor(lambda e: getattr(e, name)())

    def convert_to_v2(self) -> None:
        """Migrate the script to EisenScript v2 in place (one undo step); the notes go to the console."""
        tab = self.w.tabs.current()
        if tab is None:
            return
        result = convert_to_v2(tab.text())
        if not result.changed:
            self.w.show_message("The script is already EisenScript v2")
            return
        editing.replace_document(tab.editor, result.text)
        for note in result.notes:
            self.w.console.info(f"convert: {note}")
        self.w.show_message(f"Converted to EisenScript v2 ({len(result.notes)} notes in the console; Ctrl+Z undoes)")

    def ensure_v2(self, title: str, what: str) -> bool:
        """Makes sure the current script is EisenScript v2 before a v2 block is written into it.

        A v1 script is converted only when the user agrees (it builds the same).

        Args:
            title: The question's window title ('Add Light').
            what: What needs v2, for the question ('Lights are', 'Material blocks are').

        Returns:
            True when the script is v2 now.
        """
        tab = self.w.tabs.current()
        if tab is None:
            return False
        if tab.dialect == 2:
            return True
        question = tr("{what} EisenScript v2 blocks. Convert this script to v2 first? It builds the same.").format(
            what=what)  # fmt: skip
        buttons = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        if QMessageBox.question(self.w, title, question, buttons) != QMessageBox.StandardButton.Yes:
            return False
        self.convert_to_v2()
        return True

    def quick_fix(self) -> None:
        self._with_editor(show_quick_fixes)

    def refactor(self) -> None:
        self._with_editor(show_refactorings)

    def peek(self) -> None:
        tab = self.w.tabs.current()
        if tab is None:
            return
        _, word = tab.editor.word_at(tab.editor.textCursor().position())
        if not word or not peek_definition(tab.editor, word.split("::")[0]):
            self.w.show_message(f"'{word}' is not a rule defined in this script" if word else "No rule here")

    def fold(self) -> None:
        self._with_editor(lambda e: e.folding.fold_at(e.textCursor().blockNumber(), True))

    def unfold(self) -> None:
        self._with_editor(lambda e: e.folding.fold_at(e.textCursor().blockNumber(), False))

    def fold_all(self) -> None:
        self._with_editor(lambda e: e.folding.fold_all())

    def unfold_all(self) -> None:
        self._with_editor(lambda e: e.folding.unfold_all())

    def split(self) -> None:
        tab = self.w.tabs.current()
        if tab is not None:
            tab.toggle_split()

    # -- view options --------------------------------------------------------------------------------------
    def options(self) -> EditorOptions:
        return load_options(self.w.settings)

    def toggle(self, name: str) -> None:
        toggle_option(self.w.settings, name)
        self.apply()

    def apply(self) -> None:
        options = self.options()
        for tab in self.w.tabs.tabs():
            tab.editor.set_options(options)
            tab.breadcrumbs.setVisible(options.breadcrumbs)

    @Slot(str)
    def vim_command(self, command: str) -> None:
        """':w' saves, ':q' closes the tab, ':wq' / ':x' do both (the current tab)."""
        name = command.rstrip("!")
        if name in ("w", "wq", "x"):
            self.w.docs.save()
        if name in ("q", "wq", "x"):
            self.w.docs.close_tab()
        elif name not in ("w",):
            self.w.show_message(f"Not a Vim command here: :{command}")

    @Slot(str)
    def _preview_ready(self, rule: str) -> None:
        tab = self.w.tabs.current()
        if tab is not None:
            tab.completion.refresh_hover(rule)

    @Slot(object)
    def _on_tab_added(self, tab: EditorTab) -> None:
        tab.editor.rule_preview = lambda rule, t=tab: self.previews.image(t.text(), rule, t.seed)
        tab.editor.vim.command_entered.connect(self.vim_command)
        options = self.options()
        tab.editor.set_options(options)
        tab.breadcrumbs.setVisible(options.breadcrumbs)
