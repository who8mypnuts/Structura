"""Text-editing commands that operate on a QPlainTextEdit cursor (docs/12 §2.1). Pure helpers, no state."""

from __future__ import annotations

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QPlainTextEdit

PAIRS = {"{": "}", "[": "]", "(": ")", '"': '"'}
INDENT = "  "


def _line_range(cursor: QTextCursor) -> tuple[int, int]:
    doc = cursor.document()
    first = doc.findBlock(cursor.selectionStart()).blockNumber()
    end = cursor.selectionEnd()
    last_block = doc.findBlock(end)
    if cursor.hasSelection() and last_block.position() == end and last_block.blockNumber() > first:
        last_block = last_block.previous()  # a selection ending at column 0 excludes that line
    return first, last_block.blockNumber()


def _edit_lines(editor: QPlainTextEdit, transform: object) -> None:
    cursor = editor.textCursor()
    first, last = _line_range(cursor)
    doc = editor.document()
    cursor.beginEditBlock()
    for number in range(first, last + 1):
        block = doc.findBlockByNumber(number)
        line = QTextCursor(block)
        line.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        new = transform(block.text())  # type: ignore[operator]
        if new != block.text():
            line.insertText(new)
    cursor.endEditBlock()


def toggle_comment(editor: QPlainTextEdit) -> None:
    cursor = editor.textCursor()
    first, last = _line_range(cursor)
    doc = editor.document()
    lines = [doc.findBlockByNumber(n).text() for n in range(first, last + 1)]
    code = [line for line in lines if line.strip()]
    uncomment = bool(code) and all(line.lstrip().startswith("//") for line in code)

    def transform(line: str) -> str:
        if not line.strip():
            return line
        body = line.lstrip()
        pad = line[: len(line) - len(body)]
        if uncomment:
            return pad + body[2:].removeprefix(" ")
        return pad + "// " + body

    _edit_lines(editor, transform)


def indent(editor: QPlainTextEdit, outdent: bool = False) -> None:
    def transform(line: str) -> str:
        if outdent:
            return line[len(INDENT) :] if line.startswith(INDENT) else line.lstrip(" ")
        return INDENT + line if line.strip() else line

    _edit_lines(editor, transform)


def duplicate_line(editor: QPlainTextEdit) -> None:
    cursor = editor.textCursor()
    block = cursor.block()
    cursor.beginEditBlock()
    end = QTextCursor(block)
    end.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    end.insertText("\n" + block.text())
    cursor.endEditBlock()
    cursor.movePosition(QTextCursor.MoveOperation.Down)
    editor.setTextCursor(cursor)


def delete_line(editor: QPlainTextEdit) -> None:
    cursor = editor.textCursor()
    cursor.beginEditBlock()
    cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
    if cursor.block().blockNumber() == 0:  # the first line has no preceding newline to take with it
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QTextCursor.MoveOperation.NextBlock, QTextCursor.MoveMode.KeepAnchor)
    cursor.removeSelectedText()
    cursor.endEditBlock()


def move_line(editor: QPlainTextEdit, down: bool) -> None:
    cursor = editor.textCursor()
    block = cursor.block()
    other = block.next() if down else block.previous()
    if not other.isValid():
        return
    column = cursor.positionInBlock()
    a, b = block.text(), other.text()
    cursor.beginEditBlock()
    for target, text in ((block, b), (other, a)):
        line = QTextCursor(target)
        line.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        line.insertText(text)
    cursor.endEditBlock()
    moved = QTextCursor(editor.document().findBlockByNumber(other.blockNumber()))
    moved.movePosition(QTextCursor.MoveOperation.Right, n=min(column, len(a)))
    editor.setTextCursor(moved)


def leading_indent(text: str) -> str:
    return text[: len(text) - len(text.lstrip(" \t"))]


def newline_with_indent(editor: QPlainTextEdit) -> None:
    """Enter: keep the indentation, add a level after '{', and split '{|}' onto three lines."""
    cursor = editor.textCursor()
    block_text = cursor.block().text()
    before = block_text[: cursor.positionInBlock()]
    after = block_text[cursor.positionInBlock() :]
    pad = leading_indent(block_text)
    opens = before.rstrip().endswith("{")
    cursor.beginEditBlock()
    if opens and after.lstrip().startswith("}"):
        cursor.insertText("\n" + pad + INDENT + "\n" + pad)
        cursor.movePosition(QTextCursor.MoveOperation.Up)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    else:
        cursor.insertText("\n" + pad + (INDENT if opens else ""))
    cursor.endEditBlock()
    editor.setTextCursor(cursor)


def toggle_block_comment(editor: QPlainTextEdit) -> None:
    """Ctrl+Shift+/: wrap the selection (or the current line) in /* */, or unwrap it if already wrapped."""
    cursor = editor.textCursor()
    if not cursor.hasSelection():  # the current line, after its indentation
        block = cursor.block()
        cursor.setPosition(block.position() + len(leading_indent(block.text())))
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
    start = cursor.selectionStart()
    text = cursor.selection().toPlainText()
    stripped = text.strip()
    if stripped.startswith("/*") and stripped.endswith("*/") and len(stripped) >= 4:
        lead = text[: len(text) - len(text.lstrip())]
        trail = text[len(text.rstrip()) :]
        new = lead + stripped[2:-2].removeprefix(" ").removesuffix(" ") + trail
    else:
        new = f"/* {text} */"
    cursor.beginEditBlock()
    cursor.insertText(new)
    cursor.endEditBlock()
    cursor.setPosition(start)
    cursor.setPosition(start + len(new), QTextCursor.MoveMode.KeepAnchor)
    editor.setTextCursor(cursor)


def replace_document(editor: QPlainTextEdit, text: str) -> None:
    """Replace the whole text as one undo step, keeping the cursor's line where possible."""
    line = editor.textCursor().blockNumber()
    cursor = QTextCursor(editor.document())
    cursor.beginEditBlock()
    cursor.select(QTextCursor.SelectionType.Document)
    cursor.insertText(text)
    cursor.endEditBlock()
    block = editor.document().findBlockByNumber(min(line, editor.document().blockCount() - 1))
    editor.setTextCursor(QTextCursor(block))
