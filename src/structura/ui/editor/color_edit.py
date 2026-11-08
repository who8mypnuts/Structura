"""Colour picking in the editor (docs/12 §2.3): right-click a colour (or Ctrl+click, or Edit ▸ Pick Colour…).

The picker is not modal for the app's work: while it is open, the script follows the chosen colour (live
build shows it), Cancel restores the original, and the whole change is a single undo step. The new value
keeps the literal's style: ``#rgb`` stays three digits when it can, upper or lower case is preserved, and a
named colour stays a name when the choice is exactly a named colour.
"""

from __future__ import annotations

import re

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QColor, QTextCursor
from PySide6.QtWidgets import QColorDialog, QPlainTextEdit, QWidget

from ...core.color.names import NAMED_COLORS
from ...core.lang.highlight import lex_line
from ..i18n import tr
from .highlighter import lexer_state
from .swatches import color_of

HEX = re.compile(r"#[0-9a-fA-F]{3,12}\b")
NAME_OF = {rgb: name for name, rgb in sorted(NAMED_COLORS.items(), reverse=True)}  # first name alphabetically


def color_token_at(editor: QPlainTextEdit, position: int) -> tuple[int, str] | None:
    """(start, text) of the colour literal under ``position``: a hex colour anywhere (also in #define lines)
    or a colour name where the language expects a colour."""
    block = editor.document().findBlock(position)
    text, column = block.text(), position - block.position()
    for match in HEX.finditer(text):
        if match.start() <= column <= match.end() and color_of(match.group()) is not None:
            return block.position() + match.start(), match.group()
    tokens, _ = lex_line(text, lexer_state(block.previous().userState()))
    for start, length, role in tokens:
        word = text[start : start + length]
        if role == "color" and start <= column <= start + length and color_of(word) is not None:
            return block.position() + start, word
    return None


def _hex(color: QColor, digits: int) -> str:
    if digits == 3:
        return "#" + "".join(f"{c >> 4:x}" for c in (color.red(), color.green(), color.blue()))
    return color.name()


def format_like(original: str, color: QColor) -> str:
    """``color`` written in the style of ``original`` (see the module docstring)."""
    rgb = (color.red(), color.green(), color.blue())
    if original and not original.startswith("#"):
        name = NAME_OF.get(rgb)
        if name is not None:
            return name.upper() if original.isupper() else name.capitalize() if original[0].isupper() else name
        return color.name()
    short = all(c % 17 == 0 for c in rgb)
    text = _hex(color, 3 if short and len(original) == 4 else 6)
    upper = any(ch.isupper() for ch in original[1:])
    return text.upper() if upper else text


class ColorEdit(QObject):
    """One picking session on one literal (or an insertion point when ``text`` is empty)."""

    done = Signal()

    def __init__(self, editor: QPlainTextEdit, start: int, text: str, parent: QWidget | None = None) -> None:
        super().__init__(editor)
        self.editor, self.start, self.original = editor, start, text
        self.current = text
        self.changed = False
        initial = color_of(text) if text else QColor("#ffffff")
        self.dialog = QColorDialog(initial or QColor("#ffffff"), parent or editor)
        self.dialog.setWindowTitle(tr("Pick Colour") if text else tr("Insert Colour"))
        self.dialog.currentColorChanged.connect(self._preview)
        self.dialog.finished.connect(self._finished)

    def open(self) -> None:
        self.dialog.open()  # window-modal, but the event loop keeps running (builds, renders)

    @Slot(QColor)
    def _preview(self, color: QColor) -> None:
        if color.isValid():
            self._write(format_like(self.original, color))

    def _write(self, text: str) -> None:
        if text == self.current:
            return
        cursor = QTextCursor(self.editor.document())
        if self.changed:
            cursor.joinPreviousEditBlock()  # one undo step for the whole session
        else:
            cursor.beginEditBlock()
        cursor.setPosition(self.start)
        cursor.setPosition(self.start + len(self.current), QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(text)
        cursor.endEditBlock()
        self.current, self.changed = text, True

    @Slot(int)
    def _finished(self, result: int) -> None:
        if result == QColorDialog.DialogCode.Accepted:
            self._write(format_like(self.original, self.dialog.selectedColor()))
        elif self.changed:
            self.editor.document().undo()  # Cancel: back to the original, with nothing left on the undo stack
        self.done.emit()
        self.dialog.deleteLater()
