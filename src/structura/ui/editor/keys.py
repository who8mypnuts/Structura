"""The code editor's key bindings (docs/12 §2.1): one table of (matches, action) pairs, checked in order,
plus the typing aids (auto-closing pairs, type-over, smart dedent, block indent)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QTextCursor

from . import editing

if TYPE_CHECKING:
    from .code_editor import CodeEditor

K = Qt.Key


@dataclass(frozen=True)
class Keys:
    key: int
    text: str
    ctrl: bool
    shift: bool
    alt: bool

    @classmethod
    def of(cls, event: QKeyEvent) -> Keys:
        mods, m = event.modifiers(), Qt.KeyboardModifier
        ctrl, shift, alt = (bool(mods & flag) for flag in (m.ControlModifier, m.ShiftModifier, m.AltModifier))
        return cls(event.key(), event.text(), ctrl, shift, alt)


def next_char(editor: CodeEditor) -> str:
    cursor = editor.textCursor()
    text = cursor.block().text()
    return text[cursor.positionInBlock()] if cursor.positionInBlock() < len(text) else ""


def open_pair(editor: CodeEditor, opener: str) -> None:
    cursor = editor.textCursor()
    if cursor.hasSelection():  # surround the selection
        cursor.insertText(opener + cursor.selectedText() + editing.PAIRS[opener])
        return
    follower = next_char(editor)
    if follower and not follower.isspace() and follower not in "}])":
        cursor.insertText(opener)
        return
    cursor.insertText(opener + editing.PAIRS[opener])
    cursor.movePosition(QTextCursor.MoveOperation.Left)
    editor.setTextCursor(cursor)


def dedent_close(editor: CodeEditor) -> None:
    cursor = editor.textCursor()
    pad = editing.leading_indent(cursor.block().text())
    cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
    cursor.insertText(pad[: max(0, len(pad) - len(editing.INDENT))] + "}")
    editor.setTextCursor(cursor)


def tab(editor: CodeEditor, outdent: bool) -> None:
    cursor = editor.textCursor()
    if outdent or cursor.hasSelection():
        editing.indent(editor, outdent)
    else:
        cursor.insertText(editing.INDENT)


Binding = tuple[Callable[[Keys, "CodeEditor"], bool], Callable[[Keys, "CodeEditor"], object]]
BINDINGS: tuple[Binding, ...] = (
    (lambda k, e: k.ctrl and k.alt and k.key in (K.Key_Up, K.Key_Down),
     lambda k, e: e.multi.add_vertical(k.key == K.Key_Down)),
    (lambda k, e: k.ctrl and not k.shift and k.key == K.Key_D, lambda k, e: e.multi.add_next_occurrence()),
    (lambda k, e: k.ctrl and k.shift and k.key == K.Key_L, lambda k, e: e.multi.select_all_occurrences()),
    (lambda k, e: k.key in (K.Key_Return, K.Key_Enter) and not (k.ctrl or k.alt),
     lambda k, e: editing.newline_with_indent(e)),
    (lambda k, e: k.key == K.Key_Tab and not k.ctrl, lambda k, e: tab(e, outdent=False)),
    (lambda k, e: k.key == K.Key_Backtab, lambda k, e: tab(e, outdent=True)),
    (lambda k, e: k.ctrl and (k.key == K.Key_Question or (k.shift and k.key == K.Key_Slash)),
     lambda k, e: editing.toggle_block_comment(e)),
    (lambda k, e: k.ctrl and k.key == K.Key_Slash, lambda k, e: editing.toggle_comment(e)),
    (lambda k, e: k.alt and k.key in (K.Key_Up, K.Key_Down), lambda k, e: editing.move_line(e, k.key == K.Key_Down)),
    (lambda k, e: k.ctrl and k.shift and k.key == K.Key_D, lambda k, e: editing.duplicate_line(e)),
    (lambda k, e: k.ctrl and k.shift and k.key == K.Key_K, lambda k, e: editing.delete_line(e)),
    (lambda k, e: bool(k.text) and k.text in editing.PAIRS and not k.ctrl, lambda k, e: open_pair(e, k.text)),
    (lambda k, e: bool(k.text) and k.text in '}])"' and next_char(e) == k.text,
     lambda k, e: e.moveCursor(QTextCursor.MoveOperation.Right)),  # type over the auto-inserted closer
    (lambda k, e: k.text == "}" and not e.textCursor().block().text().strip(), lambda k, e: dedent_close(e)),
)  # fmt: skip


def handle_key(editor: CodeEditor, event: QKeyEvent) -> bool:
    """Run the first binding that matches; False lets QPlainTextEdit handle the key."""
    keys = Keys.of(event)
    for matches, action in BINDINGS:
        if matches(keys, editor):
            action(keys, editor)
            return True
    return False
