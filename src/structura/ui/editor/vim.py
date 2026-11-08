"""Vim keybindings (docs/12 §2.1, P2): normal, insert, visual and visual-line modes with counts, motions,
operators (d c y > < and ~ in visual mode), the single-key changes, '.', search and ':' commands.

An event filter in front of the editor's other key handlers (completion, multi-cursor, snippets) while on.
Insert mode passes every key through except Escape. vim_core.py parses and moves; vim_edit.py edits.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QKeyEvent, QTextCursor, QTextDocument
from PySide6.QtWidgets import QApplication

from . import vim_core as core
from . import vim_edit as edit
from .vim_prompt import VimPrompt

if TYPE_CHECKING:
    from .code_editor import CodeEditor

CHANGES = set("dc<>xXsSpPJ~rDCiaIAoO")  # commands '.' repeats
INSERTS = set("iaIAoOsSC")


class Mode(StrEnum):
    NORMAL = "normal"
    INSERT = "insert"
    VISUAL = "visual"
    VISUAL_LINE = "visual line"


KeyRecord = tuple[int, int, str]  # key, modifiers, text


class VimMode(QObject):
    mode_changed = Signal(str)  # '' when Vim keys are off
    command_entered = Signal(str)  # ':w', ':q', ':wq' … for the window; ':N' is handled here

    def __init__(self, editor: CodeEditor) -> None:
        super().__init__(editor)
        self.editor, self.enabled, self.mode = editor, False, Mode.NORMAL
        self.keys = ""  # pending normal-mode keys
        self.register: edit.Register = ("", False)
        self.goal, self.anchor, self.last_find, self.search = 0, 0, "", ""
        self.recording: list[KeyRecord] = []
        self.last_change: list[KeyRecord] = []
        self.replaying = False
        self.prompt = VimPrompt(editor, self._prompted)

    # -- switching ---------------------------------------------------------------------------------------------
    def set_enabled(self, on: bool) -> None:
        if on:
            self.editor.installEventFilter(self)  # (again:) in front of the other key filters
        if on == self.enabled:
            return
        self.enabled = on
        if on:
            self.set_mode(Mode.NORMAL)
        else:
            self.editor.removeEventFilter(self)
            self.editor.setCursorWidth(1)
            self.mode_changed.emit("")

    def set_mode(self, mode: Mode) -> None:
        self.mode = mode
        width = 1 if mode == Mode.INSERT else self.editor.fontMetrics().horizontalAdvance("M")
        self.editor.setCursorWidth(width)
        if mode in (Mode.VISUAL, Mode.VISUAL_LINE):
            self.anchor = self.pos()
            self._select(self.pos())
        self.mode_changed.emit(mode.value)

    def label(self) -> str:
        return f"-- {self.mode.value.upper()} --" if self.enabled else ""

    # -- keys --------------------------------------------------------------------------------------------------
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if not self.enabled or not isinstance(event, QKeyEvent) or event.type() != QEvent.Type.KeyPress:
            return False
        record = (event.key(), event.modifiers().value, event.text())
        if self.mode == Mode.INSERT:
            if not self.replaying:
                self.recording.append(record)
            if event.key() == Qt.Key.Key_Escape or (event.text() == "\x1b"):
                self._leave_insert()
            return False  # typing (and Escape for completion / snippets) continues normally
        return self._normal_key(event, record)

    def _normal_key(self, event: QKeyEvent, record: KeyRecord) -> bool:
        special = self._special_key(event)
        if special is not None:
            return special
        text = "j" if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) else event.text()
        if not text or not text.isprintable():
            return False  # arrows, Home, End … move the cursor natively
        if not self.keys and not self.replaying:
            self.recording = []
        self.recording.append(record)
        self.keys += text
        if self.mode != Mode.NORMAL and self._visual_key(text):
            self.keys = ""
            return True
        parsed = core.parse(self.keys)
        if parsed is not True:
            self.keys = ""
        if isinstance(parsed, core.Command):
            self._run(parsed)
        return True

    def _special_key(self, event: QKeyEvent) -> bool | None:
        """Escape (back to normal mode), Ctrl+R (redo), other Ctrl keys (the window's shortcuts); None: others."""
        if event.key() == Qt.Key.Key_Escape:
            self.keys = ""
            if self.mode != Mode.NORMAL:
                self.set_mode(Mode.NORMAL)
                edit.set_pos(self.editor, self.pos())
            return True
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_R:
                self.editor.redo()
                return True
            return False
        return None

    # -- running -----------------------------------------------------------------------------------------------
    def pos(self) -> int:
        return self.editor.textCursor().position()

    def _run(self, cmd: core.Command) -> None:
        if cmd.motion == "u" and not cmd.operator:  # undo outside an edit block
            for _ in range(cmd.count):
                self.editor.undo()
            return
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()
        try:
            if not cmd.operator and (cmd.motion in core.SIMPLE or (cmd.motion[0] == "r" and len(cmd.motion) == 2)):
                self._simple(cmd)
            else:
                self._motion(cmd)
        finally:
            cursor.endEditBlock()
        change = cmd.operator or cmd.motion[0]
        if change in CHANGES and not self.replaying and self.mode != Mode.INSERT:
            self.last_change = list(self.recording)

    def _target(self, cmd: core.Command) -> int:
        text, pos = self.editor.toPlainText(), self.pos()
        if cmd.motion == "G":
            last = text.count("\n") + (0 if text.endswith("\n") else 1)  # a final newline ends the last line
            return core.line_number_pos(text, cmd.count if cmd.explicit else last)
        if cmd.motion == "gg":
            return core.line_number_pos(text, cmd.count)
        if cmd.motion[0] in "fFtT":
            self.last_find = cmd.motion
        if cmd.motion == cmd.operator:  # dd, cc, yy, >>: count lines
            return core.vertical(text, pos, cmd.count - 1, 0)
        for _ in range(cmd.count):
            pos = core.move(text, pos, cmd.motion, self.goal, self.last_find)
        return pos

    def _motion(self, cmd: core.Command) -> None:
        target = self._target(cmd)
        if not cmd.operator:
            if cmd.motion not in "jk":
                self.goal = core.column(self.editor.toPlainText(), target)
            if self.mode in (Mode.VISUAL, Mode.VISUAL_LINE):
                self._select(target)
            else:
                edit.set_pos(self.editor, self._in_line(target))
            return
        motion = "e" if cmd.operator == "c" and cmd.motion == "w" else cmd.motion  # 'cw' changes to the word end
        if motion == "e" and cmd.motion == "w":
            target = core.move(self.editor.toPlainText(), self.pos(), "e", self.goal) if cmd.count == 1 else target
        span = core.operator_range(self.editor.toPlainText(), self.pos(), target, motion)
        self._operate(cmd.operator, span)

    def _operate(self, op: str, span: tuple[int, int, bool]) -> None:
        taken = edit.apply_operator(self.editor, op, span)
        if taken is not None:
            self.register = taken
        if op == "c":
            self.set_mode(Mode.INSERT)
        elif self.mode != Mode.NORMAL:
            self.set_mode(Mode.NORMAL)

    def _in_line(self, pos: int) -> int:
        """Normal mode never rests on a line's newline (except on an empty line)."""
        text = self.editor.toPlainText()
        return pos - 1 if pos > core.line_start(text, pos) and pos >= core.line_end(text, pos) else pos

    def _leave_insert(self) -> None:
        if not self.replaying:
            self.last_change = list(self.recording)
        self.set_mode(Mode.NORMAL)
        pos = self.pos()
        if pos > core.line_start(self.editor.toPlainText(), pos):
            edit.set_pos(self.editor, pos - 1)

    # -- visual mode -------------------------------------------------------------------------------------------
    def _select(self, pos: int) -> None:
        text = self.editor.toPlainText()
        a, b = sorted((self.anchor, pos))
        if self.mode == Mode.VISUAL_LINE:
            a, b = core.line_start(text, a), core.line_end(text, b)
        else:
            b = min(len(text), b + 1)
        start, end = (b, a) if pos < self.anchor else (a, b)  # the cursor end follows the motion
        edit.set_pos(self.editor, end, start)

    def _visual_key(self, text: str) -> bool:
        """Operators act on the selection at once; v / V switch or leave the visual modes."""
        if text in "vV":
            wanted = Mode.VISUAL if text == "v" else Mode.VISUAL_LINE
            self.set_mode(Mode.NORMAL if self.mode == wanted else wanted)
            return True
        ops = {"d": "d", "x": "d", "c": "c", "s": "c", "y": "y", ">": ">", "<": "<", "~": "~"}
        if text not in ops or self.keys != text:
            return False
        cursor = self.editor.textCursor()
        span = (cursor.selectionStart(), cursor.selectionEnd(), self.mode == Mode.VISUAL_LINE)
        if span[2] and span[1] < len(self.editor.toPlainText()):
            span = (span[0], span[1] + 1, True)
        self.last_change = list(self.recording)
        self._operate(ops[text], span)
        return True

    # -- single-key commands -----------------------------------------------------------------------------------
    def _simple(self, cmd: core.Command) -> None:
        key, n = cmd.motion, cmd.count
        text, pos = self.editor.toPlainText(), self.pos()
        if key[0] == "r":
            edit.replace_chars(self.editor, key[1], n)
        elif key in "xXsS":
            self._delete_chars(key, n, text, pos)
        elif key in "DCY":
            op, motion = {"D": ("d", "$"), "C": ("c", "$"), "Y": ("y", "y")}[key]
            self._motion(core.Command(n, op, motion))
        elif key in "pP":
            edit.paste(self.editor, self.register, key == "P", n)
        elif key in "J~":
            self._small_change(key, n, text, pos)
        elif key in "iaIAoO":
            self._insert(key, text, pos)
        else:
            self._other(key, n)

    def _delete_chars(self, key: str, n: int, text: str, pos: int) -> None:
        if key == "S":
            self._motion(core.Command(n, "c", "c"))
            return
        if key == "X":
            span = (max(core.line_start(text, pos), pos - n), pos, False)
        else:
            span = (pos, min(core.line_end(text, pos), pos + n), False)
        self._operate("c" if key == "s" else "d", span)
        if key == "x":
            edit.set_pos(self.editor, self._in_line(self.pos()))

    def _small_change(self, key: str, n: int, text: str, pos: int) -> None:
        if key == "J":
            edit.join_lines(self.editor, n + 1 if n > 1 else 1)
        else:
            end = min(core.line_end(text, pos), pos + n)
            edit.apply_operator(self.editor, "~", (pos, end, False))
            edit.set_pos(self.editor, self._in_line(end))

    def _insert(self, key: str, text: str, pos: int) -> None:
        if key in "oO":
            edit.open_line(self.editor, key == "O")
        else:
            places = {"i": pos, "I": core.first_non_blank(text, pos), "A": core.line_end(text, pos),
                      "a": min(core.line_end(text, pos), pos + 1)}  # fmt: skip
            edit.set_pos(self.editor, places[key])
        self.set_mode(Mode.INSERT)

    def _other(self, key: str, n: int) -> None:
        if key in "vV":
            self.set_mode(Mode.VISUAL if key == "v" else Mode.VISUAL_LINE)
        elif key in ":/":
            self.prompt.open(key)
        elif key in "nN":
            self.find(self.search, backward=key == "N")
        elif key == "." and self.last_change:
            self.repeat(n)

    def repeat(self, count: int = 1) -> None:
        """'.': replay the last change's keys."""
        self.replaying = True
        try:
            for _ in range(count):
                for key, mods, text in self.last_change:
                    event = QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier(mods), text)
                    QApplication.sendEvent(self.editor, event)
        finally:
            self.replaying = False

    # -- the command line --------------------------------------------------------------------------------------
    def _prompted(self, kind: str, text: str) -> None:
        if kind == "/":
            self.search = text
            self.find(text)
        elif text.strip().isdigit():
            edit.set_pos(self.editor, core.line_number_pos(self.editor.toPlainText(), int(text)))
        else:
            self.command_entered.emit(text.strip())

    def find(self, pattern: str, backward: bool = False) -> None:
        if not pattern:
            return
        flags = QTextDocument.FindFlag.FindBackward if backward else QTextDocument.FindFlag(0)
        cursor = self.editor.textCursor()
        cursor.setPosition(self.pos() + (0 if backward else 1))
        found = self.editor.document().find(pattern, cursor, flags)
        if found.isNull():  # wrap around
            start = QTextCursor(self.editor.document())
            start.movePosition(QTextCursor.MoveOperation.End if backward else QTextCursor.MoveOperation.Start)
            found = self.editor.document().find(pattern, start, flags)
        if not found.isNull():
            edit.set_pos(self.editor, found.selectionStart())
