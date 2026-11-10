"""File and editing actions of the main window (new/open/save, find, insert, definitions, colours)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QPoint, QUrl, Slot
from PySide6.QtGui import QAction, QDesktopServices, QGuiApplication, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMenu, QMessageBox

from ..core.lang.refactor import format_script, rename_rule, rule_occurrences
from ..core.project.model import SUFFIX
from ..core.text_file import read_script
from ..services.backups import back_up
from ..services.recent import RecentFiles
from .documents import NEW_SCRIPT_V2, EditorTab
from .editor.color_edit import ColorEdit, color_token_at
from .editor.editing import toggle_comment
from .editor.snippet_session import insert_snippet
from .i18n import tr
from .legacy_save import LegacySave
from .save_paths import SavePaths, with_extension
from .theming import qcolor

if TYPE_CHECKING:
    from .app_window import MainWindow

SCRIPT_FILTER = f"EisenScript (*.es);;Structura project (*{SUFFIX});;All files (*)"
OPEN_FILTER = f"Scripts and projects (*.es *{SUFFIX});;{SCRIPT_FILTER}"
EDITOR_MENU = ("edit.definition", "edit.peek", "edit.references", "edit.rename", "edit.quick_fix", "edit.refactor",
               "edit.comment", "edit.format")  # fmt: skip


class DocumentActions(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.legacy = LegacySave(window)
        self.w = window
        window.tabs.tab_added.connect(self.on_tab_added)
        self.recent = RecentFiles(window.settings)
        self.paths = SavePaths(window.settings)
        self.backups = window.settings.directory() / "backups"
        window.tabs.external_change.connect(self.on_external_change)
        window.tabs.save_tab = self.save  # closing a modified tab offers to save it
        window.tabs.tabBar().customContextMenuRequested.connect(self.tab_menu)

    def current(self) -> EditorTab | None:
        return self.w.tabs.current()

    # -- files ---------------------------------------------------------------------------------------------
    def new_script(self) -> EditorTab:
        return self.w.tabs.new_document()

    def new_v2_script(self) -> EditorTab:
        """File ▸ New v2 Script: a starter with a material, glass, a sun, a sky and a ground."""
        return self.w.tabs.new_document(NEW_SCRIPT_V2)

    def open_dialog(self) -> None:
        tab = self.current()
        start = self.paths.folder("script", tab.path if tab is not None else None)
        name, _ = QFileDialog.getOpenFileName(self.w, tr("Open Script"), str(start), OPEN_FILTER)
        if name:
            self.paths.remember("script", Path(name))
            self.open_file(Path(name))

    @Slot(Path)
    def open_file(self, path: Path) -> EditorTab | None:
        if path.suffix == SUFFIX:
            return self.w.projects.open(path)
        tab = self.w.tabs.open_file(path)
        self.recent.add(path)
        return tab

    def fill_recent_menu(self, menu: QMenu) -> None:
        """File ▸ Open Recent, rebuilt each time it opens."""
        menu.clear()
        paths = self.recent.paths()
        for path in paths:
            menu.addAction(f"{path.name}    {path.parent}").triggered.connect(
                lambda _c=False, p=path: self.open_file(p)
            )
        if not paths:
            menu.addAction("No recent files").setEnabled(False)
        else:
            menu.addSeparator()
            menu.addAction("Clear Recent Files").triggered.connect(self.recent.clear)

    def save(self, tab: EditorTab | None = None) -> bool:
        """File ▸ Save (the current tab, or ``tab``): True when it was saved (Save As can be cancelled)."""
        tab = tab or self.current()
        if tab is None:
            return False
        if tab.project_path is not None:
            return self.w.projects.save(tab)
        if tab.path is None:
            return self.save_as(tab)
        self.write(tab)
        self.w.show_message(f"Saved {tab.path.name}")
        return True

    def write(self, tab: EditorTab, path: Path | None = None) -> None:
        """Save ``tab`` (to ``path``), keeping a backup of the file it replaces (services/backups.py)."""
        target = path or tab.path
        if target is not None:
            try:
                back_up(target, self.backups)
            except OSError as exc:  # a backup never stops a save
                self.w.console.info(f"No backup of {target.name}: {exc}")
        tab.save(path)

    def open_example(self, path: Path) -> EditorTab:
        """A bundled example opens as an unsaved copy (Save As offers its name; the original stays untouched)."""
        tab = self.w.tabs.new_document(read_script(path))
        tab.suggested_name = path.name
        tab.editor.document().setModified(False)
        tab.retitle()
        self.w.tabs.setTabText(self.w.tabs.indexOf(tab), tab.title)
        return tab

    def save_as(self, tab: EditorTab | None = None) -> bool:
        tab = tab or self.current()
        if tab is None:
            return False
        suggestion = tab.path or self.paths.suggest("script", tab.suggested_name or "untitled.es")
        answer = self.paths.ask(self.w, "script", tr("Save Script"), suggestion, SCRIPT_FILTER.split(";;"))
        if answer is None:
            return False
        self.write(tab, Path(with_extension(answer[0], (".es", SUFFIX))))
        self.w.tabs.watch(tab)
        tab.retitle()
        return True

    def tab_menu(self, pos: QPoint) -> None:
        """The tab bar's context menu: close (this, others, to the right, saved), save, and the file's place."""
        tabs = self.w.tabs
        index = tabs.tabBar().tabAt(pos)
        tab = tabs.widget(index)
        if not isinstance(tab, EditorTab):
            return
        count, menu = tabs.count(), QMenu(tabs)
        saved = [i for i, t in enumerate(tabs.tabs()) if not t.modified]
        entries = (
            (tr("Close"), lambda: tabs.close_tab(index), True),
            (tr("Close Others"), lambda: tabs.close_tabs([i for i in range(count) if i != index]), count > 1),
            (tr("Close to the Right"), lambda: tabs.close_tabs(list(range(index + 1, count))), index < count - 1),
            (tr("Close Saved"), lambda: tabs.close_tabs(saved), bool(saved)),
            None,
            (tr("Save"), lambda: self.save(tab), True),
            (tr("Save As…"), lambda: self.save_as(tab), True),
            None,
            (tr("Copy Path"), lambda: QGuiApplication.clipboard().setText(str(tab.path)), tab.path is not None),
            (tr("Reveal in Folder"), lambda: self.reveal(tab), tab.path is not None),
        )  # fmt: skip
        for entry in entries:
            if entry is None:
                menu.addSeparator()
                continue
            title, handler, enabled = entry
            action = menu.addAction(title)
            action.setEnabled(enabled)
            action.triggered.connect(lambda _checked=False, h=handler: h())
        menu.popup(tabs.tabBar().mapToGlobal(pos))

    def reveal(self, tab: EditorTab) -> None:
        if tab.path is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(tab.path.parent)))

    def revert(self) -> None:
        """Reload the file from disk, discarding unsaved edits (after asking)."""
        tab = self.current()
        if tab is None or tab.path is None or not tab.path.exists():
            return
        if tab.modified:
            question = f"Discard your changes to {tab.path.name} and reload it from disk?"
            if QMessageBox.question(self.w, "Revert", question) != QMessageBox.StandardButton.Yes:
                return
        tab.reload(read_script(tab.path))

    def close_tab(self) -> None:
        self.w.tabs.close_tab(self.w.tabs.currentIndex())

    @Slot(object)
    def on_external_change(self, tab: EditorTab) -> None:
        name = tab.path.name if tab.path else "the file"
        question = f"{name} changed on disk. Discard your edits and reload it?"
        answer = QMessageBox.question(self.w, "File changed on disk", question)
        if answer == QMessageBox.StandardButton.Yes and tab.path is not None:
            tab.reload(read_script(tab.path))

    # -- editing -------------------------------------------------------------------------------------------
    def open_find(self, replace_mode: bool) -> None:
        tab = self.current()
        if tab is not None:
            tab.find_bar.open(replace_mode)

    def insert_text(self, text: str) -> None:
        tab = self.current()
        if tab is not None:
            insert_snippet(tab.editor, text)  # plain text, or a snippet with tab stops
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
                self.replace_text(tab, rename_rule(tab.text(), name, new))
            except ValueError as exc:
                self.w.show_message(str(exc))

    def format_document(self) -> None:
        tab = self.current()
        if tab is not None:
            formatted = format_script(tab.text())
            if formatted != tab.text():
                self.replace_text(tab, formatted)

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

    def replace_text(self, tab: EditorTab, text: str) -> None:
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
        tab.editor.definition_requested.connect(self.go_to_definition)
        tab.editor.color_requested.connect(self.pick_color)
        tab.editor.menu_extender = self.extend_menu

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
        """Edit the colour literal at ``start`` (or insert one when ``text`` is empty) with a live preview."""
        tab = self.current()
        if tab is not None:
            ColorEdit(tab.editor, start, text, self.w).open()

    def pick_color_at_cursor(self) -> None:
        tab = self.current()
        if tab is not None:
            position = tab.editor.textCursor().position()
            self.pick_color(*(color_token_at(tab.editor, position) or (position, "")))

    def extend_menu(self, menu: QMenu, before: QAction) -> None:
        """The editor's context menu: the language commands above the standard edit actions."""
        for command_id in EDITOR_MENU:
            menu.insertAction(before, self.w.registry.action(command_id))
