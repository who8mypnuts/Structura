"""Number scrubbing (docs/12 §2.3): Alt+drag over a number changes it; Shift = fine, Ctrl = coarse.
Integers stay integers; the whole drag is one undo step."""

from __future__ import annotations

import re
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QPlainTextEdit

NUMBER = re.compile(r"[+-]?(\d+\.?\d*|\.\d+)")
PIXELS_PER_STEP = 4


@dataclass
class Scrub:
    start: int  # document position of the number
    length: int
    value: float
    decimals: int
    origin_x: float
    changed: bool = False  # the text is only touched once the drag changes the value


def number_at(editor: QPlainTextEdit, position: int) -> tuple[int, str] | None:
    """(start position, text) of the number containing ``position``."""
    block = editor.document().findBlock(position)
    column = position - block.position()
    for m in NUMBER.finditer(block.text()):
        if m.start() <= column <= m.end():
            return block.position() + m.start(), m.group(0)
    return None


def step_size(decimals: int, modifiers: Qt.KeyboardModifier) -> float:
    """One step changes the last shown digit; Ctrl makes steps ten times larger."""
    base = 10.0**-decimals
    return base * 10.0 if modifiers & Qt.KeyboardModifier.ControlModifier else base


def format_value(value: float, decimals: int) -> str:
    return str(round(value)) if decimals == 0 else f"{value:.{decimals}f}"


class Scrubber:
    def __init__(self, editor: QPlainTextEdit) -> None:
        self.editor = editor
        self.active: Scrub | None = None

    def begin(self, position: int, x: float) -> bool:
        found = number_at(self.editor, position)
        if found is None:
            return False
        start, text = found
        decimals = len(text.split(".")[1]) if "." in text else 0
        self.active = Scrub(start, len(text), float(text), decimals, x)
        return True

    def move(self, x: float, modifiers: Qt.KeyboardModifier) -> None:
        if self.active is None:
            return
        s = self.active
        fine = bool(modifiers & Qt.KeyboardModifier.ShiftModifier) and s.decimals > 0
        decimals = s.decimals + (1 if fine else 0)  # fine steps on decimals show one more digit
        steps = int((x - s.origin_x) / PIXELS_PER_STEP)
        if steps == 0 and not s.changed:
            return
        value = s.value + steps * step_size(decimals, modifiers & ~Qt.KeyboardModifier.ShiftModifier)
        self._replace(format_value(value, decimals), first=not s.changed)
        s.changed = True

    def end(self) -> bool:
        """Finish; True when the drag changed the number (False: it was a plain Alt+click)."""
        changed = self.active is not None and self.active.changed
        self.active = None
        return changed

    def _replace(self, text: str, first: bool = False) -> None:
        s = self.active
        assert s is not None
        cursor = QTextCursor(self.editor.document())
        if first:
            cursor.beginEditBlock()
        else:
            cursor.joinPreviousEditBlock()
        cursor.setPosition(s.start)
        cursor.setPosition(s.start + s.length, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(text)
        cursor.endEditBlock()
        s.length = len(text)
