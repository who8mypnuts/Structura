"""File and editing actions of the main window (new/open/save, find, insert, definitions, colours)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Slot
from PySide6.QtGui import QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QColorDialog, QFileDialog, QInputDialog, QMessageBox

from ..core.lang.refactor import format_script, rename_rule, rule_occurrences
from .documents import EditorTab, read_text
from .editor.editing import toggle_comment
from .editor.swatches import color_of
from .theming import qcolor

if TYPE_CHECKING:
    from .app_window import MainWindow

SCRIPT_FILTER = "EisenScript (*.es);;All files (*)"


class DocumentActions(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        window.tabs.tab_added.connect(self.on_tab_added)
        window.tabs.external_change.connect(self.on_external_change)

    def current(self) -> EditorTab | None:
        return self.w.tabs.current()

    # -- files ---------------------------------------------------------------------------------------------
    def new_script(self) -> EditorTab:
        return self.w.tabs.new_document()

    def open_dialog(self) -> None:
        name, _ = QFileDialog.getOpenFileName(self.w, "Open script", "", SCRIPT_FILTER)
        if name:
            self.open_file(Path(name))

    @Slot(Path)
    def open_file(self, path: Path) -> EditorTab:
        tab = self.w.tabs.open_file(path)
        self.w.settings.set_value("files/last", str(path))
        return tab

    def save(self) -> None:
        tab = self.current()
        if tab is None:
            return
        if tab.path is None:
            self.save_as()
        else:
            tab.save()
            self.w.show_message(f"Saved {tab.path.name}")

    def save_as(self) -> None:
        tab = self.current()
        if tab is None:
            return
        name, _ = QFileDialog.getSaveFileName(self.w, "Save script", str(tab.path or "untitled.es"), SCRIPT_FILTER)
        if name:
            tab.save(Path(name))
            self.w.tabs.watch(tab)
            self.w.tabs.setTabText(self.w.tabs.currentIndex(), tab.title)

    def close_tab(self) -> None:
        self.w.tabs.close_tab(self.w.tabs.currentIndex())

    @Slot(object)
    def on_external_change(self, tab: EditorTab) -> None:
        name = tab.path.name if tab.path else "the file"
        question = f"{name} changed on disk. Discard your edits and reload it?"
        answer = QMessageBox.question(self.w, "File changed on disk", question)
        if answer == QMessageBox.StandardButton.Yes and tab.path is not None:
            tab.reload(read_text(tab.path))

    # -- editing -------------------------------------------------------------------------------------------
    def open_find(self, replace_mode: bool) -> None:
        tab = self.current()
        if tab is not None:
            tab.find_bar.open(replace_mode)

    def insert_text(self, text: str) -> None:
        tab = self.current()
        if tab is not None:
            tab.editor.textCursor().insertText(text)
            tab.editor.setFocus()

    def toggle_comment(self) -> None:
        tab = self.current()
        if tab is not None:
            toggle_comment(tab.editor)

    def zoom(self, steps: int) -> None:
        tab = self.current()
        if tab is not None:
            tab.editor.zoom(steps)

    @Slot(int)
    def go_to(self, offset: int) -> None:
        tab = self.current()
        if tab is not None:
            tab.editor.go_to(offset)

    def rename_rule(self) -> None:
        tab = self.current()
        if tab is None:
            return
        _, word = tab.editor.word_at(tab.editor.textCursor().position())
        name = word.split("::")[0]
        if not rule_occurrences(tab.text(), name):
            self.w.show_message("Place the cursor on a rule name to rename it (F2).")
            return
        new, ok = QInputDialog.getText(self.w, "Rename rule", f"New name for '{name}':", text=name)
        if ok and new and new != name:
            try:
                self._replace_all(tab, rename_rule(tab.text(), name, new))
            except ValueError as exc:
                self.w.show_message(str(exc))

    def format_document(self) -> None:
        tab = self.current()
        if tab is not None:
            formatted = format_script(tab.text())
            if formatted != tab.text():
                self._replace_all(tab, formatted)

    def find_references(self) -> None:
        tab = self.current()
        if tab is None:
            return
        _, word = tab.editor.word_at(tab.editor.textCursor().position())
        spans = rule_occurrences(tab.text(), word.split("::")[0])
        fmt = QTextCharFormat()
        fmt.setBackground(qcolor(tab.editor.theme["editor.find.match"]))
        tab.editor.set_selections("find", [tab.editor.selection_for(a, b, fmt) for a, b in spans])
        self.w.show_message(f"{len(spans)} occurrence{'s' if len(spans) != 1 else ''} of '{word}'")

    def _replace_all(self, tab: EditorTab, text: str) -> None:
        """Replace the whole text as one undo step, keeping the cursor position."""
        cursor = tab.editor.textCursor()
        position = cursor.position()
        cursor.beginEditBlock()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.insertText(text)
        cursor.endEditBlock()
        cursor.setPosition(min(position, len(text)))
        tab.editor.setTextCursor(cursor)

    @Slot(object)
    def on_tab_added(self, tab: EditorTab) -> None:
        tab.editor.set_font_size(self.w.fonts().code_size)
        tab.editor.definition_requested.connect(self.go_to_definition)
        tab.editor.color_requested.connect(self.pick_color)

    @Slot(str)
    def go_to_definition(self, name: str) -> None:
        tab = self.current()
        analysis = tab.analysis if tab else None
        if tab is None or analysis is None:
            return
        rule = next((r for r in analysis.rules if r.name == name.lower()), None)
        if rule is not None:
            tab.editor.go_to(rule.span.start)
        else:
            self.w.show_message(f"'{name}' is not a rule defined in this script")

    def definition_under_cursor(self) -> None:
        tab = self.current()
        if tab is not None:
            _, word = tab.editor.word_at(tab.editor.textCursor().position())
            if word:
                self.go_to_definition(word.split("::")[0])

    @Slot(int, str)
    def pick_color(self, start: int, text: str) -> None:
        tab = self.current()
        initial = color_of(text)
        if tab is None or initial is None:
            return
        chosen = QColorDialog.getColor(initial, self.w, "Colour")
        if chosen.isValid():
            cursor = tab.editor.textCursor()
            cursor.setPosition(start)
            cursor.setPosition(start + len(text), QTextCursor.MoveMode.KeepAnchor)
            cursor.insertText(chosen.name())
