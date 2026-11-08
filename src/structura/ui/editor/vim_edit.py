"""Vim keybindings, the editing half (docs/12 §2.1, P2): the operators and single-key changes, applied to the
editor's document as one undo step each. ui/editor/vim.py decides what to run."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QTextCursor

from . import editing
from .vim_core import first_non_blank, line_end, line_start

if TYPE_CHECKING:
    from PySide6.QtWidgets import QPlainTextEdit

Register = tuple[str, bool]  # text, linewise


def text_of(editor: QPlainTextEdit) -> str:
    return editor.toPlainText()


def set_pos(editor: QPlainTextEdit, pos: int, anchor: int | None = None) -> None:
    cursor = editor.textCursor()
    size = max(0, editor.document().characterCount() - 1)
    if anchor is not None:
        cursor.setPosition(max(0, min(anchor, size)))
    cursor.setPosition(max(0, min(pos, size)), QTextCursor.MoveMode.KeepAnchor if anchor is not None else
                       QTextCursor.MoveMode.MoveAnchor)  # fmt: skip
    editor.setTextCursor(cursor)


def replace_range(editor: QPlainTextEdit, start: int, end: int, new: str) -> None:
    cursor = QTextCursor(editor.document())
    cursor.setPosition(start)
    cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
    cursor.insertText(new)


def apply_operator(editor: QPlainTextEdit, op: str, span: tuple[int, int, bool]) -> Register | None:
    """d, c, y, >, <, ~ over [start, end); returns what d, c and y put in the register. After 'c' the caller
    enters insert mode at the cursor."""
    start, end, linewise = span
    text = text_of(editor)
    taken = text[start:end]
    if op in "<>":
        set_pos(editor, max(start, end - 1), start)
        editing.indent(editor, outdent=op == "<")
        set_pos(editor, first_non_blank(text_of(editor), start))
        return None
    if op == "~":
        replace_range(editor, start, end, taken.swapcase())
        set_pos(editor, start)
        return None
    if op == "y":
        set_pos(editor, start)
        return taken, linewise
    if op == "c" and linewise:
        pad = editing.leading_indent(text[start : line_end(text, start)])
        replace_range(editor, start, end, pad + ("\n" if taken.endswith("\n") else ""))
        set_pos(editor, start + len(pad))
        return taken, linewise
    replace_range(editor, start, end, "")
    after = text_of(editor)
    set_pos(editor, first_non_blank(after, start) if linewise and op == "d" else start)
    return taken, linewise


def paste(editor: QPlainTextEdit, register: Register, before: bool, count: int) -> None:
    content, linewise = register
    if not content:
        return
    text, pos = text_of(editor), editor.textCursor().position()
    body = content * count
    if linewise:
        body = body if body.endswith("\n") else body + "\n"
        at = line_start(text, pos) if before else line_end(text, pos) + 1
        if at > len(text):  # after the last line, which has no newline
            replace_range(editor, len(text), len(text), "\n" + body.rstrip("\n"))
            set_pos(editor, len(text) + 1)
            return
        replace_range(editor, at, at, body)
        set_pos(editor, first_non_blank(text_of(editor), at))
        return
    at = pos if before or line_start(text, pos) == line_end(text, pos) else pos + 1
    replace_range(editor, at, at, body)
    set_pos(editor, at + len(body) - 1)


def join_lines(editor: QPlainTextEdit, count: int) -> None:
    for _ in range(max(1, count - 1) if count > 1 else 1):
        text, pos = text_of(editor), editor.textCursor().position()
        end = line_end(text, pos)
        if end >= len(text):
            return
        nxt = end + 1
        while nxt < len(text) and text[nxt] in " \t":
            nxt += 1
        replace_range(editor, end, nxt, " " if nxt < len(text) and text[nxt] != "\n" else "")
        set_pos(editor, end)


def replace_chars(editor: QPlainTextEdit, ch: str, count: int) -> None:
    text, pos = text_of(editor), editor.textCursor().position()
    if pos + count > line_end(text, pos):
        return
    replace_range(editor, pos, pos + count, ch * count)
    set_pos(editor, pos + count - 1)


def open_line(editor: QPlainTextEdit, above: bool) -> None:
    """'o' / 'O': a new line below / above with the current line's indentation; the cursor goes there."""
    text, pos = text_of(editor), editor.textCursor().position()
    pad = editing.leading_indent(text[line_start(text, pos) : line_end(text, pos)])
    if above:
        at = line_start(text, pos)
        replace_range(editor, at, at, pad + "\n")
        set_pos(editor, at + len(pad))
        return
    at = line_end(text, pos)
    replace_range(editor, at, at, "\n" + pad)
    set_pos(editor, at + 1 + len(pad))
