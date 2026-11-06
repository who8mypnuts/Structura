"""Multiple cursors (docs/12 §2.1): Alt+click, Ctrl+D (next occurrence), Ctrl+Shift+L (all occurrences),
Ctrl+Alt+Up/Down and Alt+Shift+drag (column selection). The editor's own cursor is the primary one; the
extra cursors live here. Typing, deleting and moving apply to every cursor as one undo step; Esc or a plain
click returns to a single cursor."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QKeyEvent, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QTextEdit

from ..theming import qcolor

if TYPE_CHECKING:
    from .code_editor import CodeEditor

Move = QTextCursor.MoveOperation
MOVES = {
    Qt.Key.Key_Left: Move.Left, Qt.Key.Key_Right: Move.Right, Qt.Key.Key_Up: Move.Up, Qt.Key.Key_Down: Move.Down,
    Qt.Key.Key_Home: Move.StartOfLine, Qt.Key.Key_End: Move.EndOfLine,
}  # fmt: skip


class MultiCursor(QObject):
    def __init__(self, editor: CodeEditor) -> None:
        super().__init__(editor)
        self.editor = editor
        self.extra: list[QTextCursor] = []
        editor.installEventFilter(self)

    @property
    def active(self) -> bool:
        return bool(self.extra)

    def cursors(self) -> list[QTextCursor]:
        return [self.editor.textCursor(), *self.extra]

    # -- adding cursors ------------------------------------------------------------------------------------
    def add_at(self, position: int) -> None:
        cursor = QTextCursor(self.editor.document())
        cursor.setPosition(position)
        if all(c.position() != position for c in self.cursors()):
            self.extra.append(cursor)
        self.refresh()

    def add_next_occurrence(self) -> None:
        """Ctrl+D: select the word at the cursor first; then add the next match of the selection."""
        primary = self.editor.textCursor()
        if not primary.hasSelection():
            primary.select(QTextCursor.SelectionType.WordUnderCursor)
            self.editor.setTextCursor(primary)
            return self.refresh()
        needle = primary.selectedText()
        last = max(self.cursors(), key=lambda c: c.selectionEnd())
        found = self.editor.document().find(needle, last.selectionEnd())
        if found.isNull():
            found = self.editor.document().find(needle, 0)  # wrap around
        if not found.isNull() and all(c.selectionStart() != found.selectionStart() for c in self.cursors()):
            self.extra.append(found)
        return self.refresh()

    def select_all_occurrences(self) -> None:
        primary = self.editor.textCursor()
        if not primary.hasSelection():
            primary.select(QTextCursor.SelectionType.WordUnderCursor)
            self.editor.setTextCursor(primary)
        needle = self.editor.textCursor().selectedText()
        if not needle:
            return
        found, self.extra = self.editor.document().find(needle, 0), []
        while not found.isNull():
            if found.selectionStart() != self.editor.textCursor().selectionStart():
                self.extra.append(QTextCursor(found))
            found = self.editor.document().find(needle, found.selectionEnd())
        self.refresh()

    def add_vertical(self, down: bool) -> None:
        """Ctrl+Alt+Up/Down: a cursor on the line above/below the outermost cursor, same column."""
        edge = (max if down else min)(self.cursors(), key=lambda c: c.position())
        cursor = QTextCursor(edge)
        cursor.clearSelection()
        column = cursor.positionInBlock()
        if not cursor.movePosition(Move.NextBlock if down else Move.PreviousBlock):
            return
        cursor.movePosition(Move.Right, n=min(column, cursor.block().length() - 1))
        self.add_at(cursor.position())

    def column_select(self, anchor: int, position: int) -> None:
        """Alt+Shift+drag: one selection per line between the two points, over the same columns."""
        doc = self.editor.document()
        a, b = doc.findBlock(anchor), doc.findBlock(position)
        first_col, last_col = anchor - a.position(), position - b.position()
        lines = range(min(a.blockNumber(), b.blockNumber()), max(a.blockNumber(), b.blockNumber()) + 1)
        cursors = []
        for number in lines:
            block = doc.findBlockByNumber(number)
            length = block.length() - 1
            cursor = QTextCursor(block)
            cursor.setPosition(block.position() + min(first_col, length))
            cursor.setPosition(block.position() + min(last_col, length), QTextCursor.MoveMode.KeepAnchor)
            cursors.append(cursor)
        if cursors:
            self.editor.setTextCursor(cursors[-1])
            self.extra = cursors[:-1]
        self.refresh()

    def clear(self) -> None:
        if self.extra:
            self.extra = []
            self.refresh()

    # -- editing ---------------------------------------------------------------------------------------------
    def _edit(self, action: object) -> None:
        """Apply ``action(cursor)`` at every cursor (last first, so earlier positions stay valid), one undo."""
        primary = self.editor.textCursor()
        primary.beginEditBlock()
        for cursor in sorted([*self.extra, primary], key=lambda c: c.position(), reverse=True):
            action(cursor)  # type: ignore[operator]
        primary.endEditBlock()
        self.editor.setTextCursor(primary)
        self._merge()
        self.refresh()

    def _move(self, operation: QTextCursor.MoveOperation, select: bool) -> None:
        mode = QTextCursor.MoveMode.KeepAnchor if select else QTextCursor.MoveMode.MoveAnchor
        primary = self.editor.textCursor()
        for cursor in [primary, *self.extra]:
            cursor.movePosition(operation, mode)
        self.editor.setTextCursor(primary)
        self._merge()
        self.refresh()

    def _merge(self) -> None:
        """Drop extra cursors that collapsed onto another cursor."""
        seen = {self.editor.textCursor().position()}
        kept = []
        for cursor in self.extra:
            if cursor.position() not in seen:
                seen.add(cursor.position())
                kept.append(cursor)
        self.extra = kept

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if not self.extra or not isinstance(event, QKeyEvent) or event.type() != QEvent.Type.KeyPress:
            return False
        return self._key(event)

    def _key(self, event: QKeyEvent) -> bool:
        key, mods, text = event.key(), event.modifiers(), event.text()
        if key == Qt.Key.Key_Escape:
            self.clear()
        elif key in MOVES and not mods & Qt.KeyboardModifier.ControlModifier:
            self._move(MOVES[Qt.Key(key)], bool(mods & Qt.KeyboardModifier.ShiftModifier))
        elif key == Qt.Key.Key_Backspace:
            self._edit(lambda c: c.deletePreviousChar())
        elif key == Qt.Key.Key_Delete:
            self._edit(lambda c: c.deleteChar())
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._edit(lambda c: c.insertText("\n"))
        elif text and text.isprintable() and not mods & Qt.KeyboardModifier.ControlModifier:
            self._edit(lambda c: c.insertText(text))
        else:
            return False
        return True

    # -- display -----------------------------------------------------------------------------------------------
    def refresh(self) -> None:
        fmt = QTextCharFormat()
        fmt.setBackground(qcolor(self.editor.theme["editor.selection"]))
        selections = []
        for cursor in self.extra:
            if cursor.hasSelection():
                selection = QTextEdit.ExtraSelection()
                selection.cursor, selection.format = QTextCursor(cursor), fmt
                selections.append(selection)
        self.editor.set_selections("multi", selections)
        self.editor.viewport().update()
