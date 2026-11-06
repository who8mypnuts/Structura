"""The EisenScript code editor (docs/12). A composition root: highlighting, the gutter, bracket matching,
diagnostic squiggles and editing helpers each live in their own module."""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QResizeEvent,
    QTextCharFormat,
    QTextCursor,
    QTextFormat,
    QWheelEvent,
)
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

from ...core.lang.analysis import Analysis
from ...core.lang.diagnostics import Diagnostic, Severity
from ...core.lang.highlight import lex_line
from ...themes.model import Theme
from ..fonts import code_font
from ..theming import qcolor
from . import editing
from .brackets import match_bracket
from .gutter import Gutter
from .highlighter import EisenHighlighter
from .inlays import paint_inlays
from .scrubber import Scrubber
from .swatches import color_of, paint_swatches

DIAG_ROLE = {Severity.ERROR: "diag.error", Severity.WARNING: "diag.warning", Severity.INFO: "diag.info"}


class CodeEditor(QPlainTextEdit):
    cursor_moved = Signal(int, int)  # line, column (1-based)
    definition_requested = Signal(str)  # Ctrl+click / F12 on a rule name
    color_requested = Signal(int, str)  # Ctrl+click on a colour literal: (start position, text)

    def __init__(self, theme: Theme, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("CodeEditor")
        self.setFont(code_font())
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 2)
        self.theme = theme
        self.highlighter = EisenHighlighter(self.document(), theme)
        self.gutter = Gutter(self)
        self.diagnostics: list[Diagnostic] = []
        self.analysis: Analysis | None = None  # the latest analysis of this text (completion, hover)
        self._selections: dict[str, list[QTextEdit.ExtraSelection]] = {}
        self.blockCountChanged.connect(self._update_margins)
        self.updateRequest.connect(self._update_gutter)
        self.cursorPositionChanged.connect(self._on_cursor)
        self.setMouseTracking(True)
        self.scrubber = Scrubber(self)
        self.set_theme(theme)
        self._update_margins()

    # -- theme -------------------------------------------------------------------------------------------
    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.highlighter.set_theme(theme)
        self.gutter.colors = {
            "fg": qcolor(theme["editor.line.number"]),
            "active": qcolor(theme["editor.line.number.active"]),
            "bg": qcolor(theme["editor.bg"]),
        }
        self.set_diagnostics(self.diagnostics)
        self._on_cursor()

    # -- layout & gutter -----------------------------------------------------------------------------------
    def _update_margins(self) -> None:
        self.setViewportMargins(self.gutter.width_needed(), 0, 0, 0)

    def _update_gutter(self, rect: QRect, dy: int) -> None:
        if dy:
            self.gutter.scroll(0, dy)
        else:
            self.gutter.update(0, rect.y(), self.gutter.width(), rect.height())

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        r = self.contentsRect()
        self.gutter.setGeometry(QRect(r.left(), r.top(), self.gutter.width_needed(), r.height()))

    # -- extra selections (current line, brackets, diagnostics) ----------------------------------------------
    def set_selections(self, layer: str, selections: list[QTextEdit.ExtraSelection]) -> None:
        self._selections[layer] = selections
        order = ("line", "find", "brackets", "diagnostics")
        self.setExtraSelections([s for key in order for s in self._selections.get(key, [])])

    def selection_for(self, start: int, end: int, fmt: QTextCharFormat) -> QTextEdit.ExtraSelection:
        sel = QTextEdit.ExtraSelection()
        cursor = QTextCursor(self.document())
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        sel.cursor, sel.format = cursor, fmt
        return sel

    def _on_cursor(self) -> None:
        line = QTextEdit.ExtraSelection()
        line.format.setBackground(qcolor(self.theme["editor.line.current"]))
        line.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        line.cursor = self.textCursor()
        line.cursor.clearSelection()
        brackets = []
        match = match_bracket(self.toPlainText(), self.textCursor().position())
        if match is not None:
            fmt = QTextCharFormat()
            fmt.setBackground(qcolor(self.theme["editor.bracket.match"]))
            brackets = [self.selection_for(p, p + 1, fmt) for p in match]
        self.set_selections("line", [line])
        self.set_selections("brackets", brackets)
        cursor = self.textCursor()
        self.cursor_moved.emit(cursor.blockNumber() + 1, cursor.positionInBlock() + 1)
        self.gutter.update()

    # -- diagnostics ---------------------------------------------------------------------------------------
    def set_diagnostics(self, diagnostics: list[Diagnostic]) -> None:
        self.diagnostics = list(diagnostics)
        selections: list[QTextEdit.ExtraSelection] = []
        markers: dict[int, tuple[Severity, QColor]] = {}
        length = self.document().characterCount()
        for d in self.diagnostics:
            color = qcolor(self.theme[DIAG_ROLE.get(d.severity, "diag.hint")])
            if d.span is None:
                continue
            start = min(d.span.start, max(0, length - 1))
            end = max(start + 1, min(d.span.end, length - 1))
            fmt = QTextCharFormat()
            fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
            fmt.setUnderlineColor(color)
            selections.append(self.selection_for(start, end, fmt))
            number = self.document().findBlock(start).blockNumber()
            if number not in markers or markers[number][0] < d.severity:
                markers[number] = (d.severity, color)
        self.gutter.markers = markers
        self.set_selections("diagnostics", selections)
        self.gutter.update()

    def diagnostic_at(self, pos: int) -> Diagnostic | None:
        for d in self.diagnostics:
            if d.span is not None and d.span.start <= pos <= max(d.span.end, d.span.start + 1):
                return d
        return None

    # -- typing aids ---------------------------------------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if not self._handle_key(event):
            super().keyPressEvent(event)

    def _handle_key(self, event: QKeyEvent) -> bool:
        key, mods, text = event.key(), event.modifiers(), event.text()
        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
        shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)
        alt = bool(mods & Qt.KeyboardModifier.AltModifier)
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (ctrl or alt):
            editing.newline_with_indent(self)
        elif key == Qt.Key.Key_Tab and not ctrl:
            self._tab(outdent=False)
        elif key == Qt.Key.Key_Backtab:
            self._tab(outdent=True)
        elif ctrl and key == Qt.Key.Key_Slash:
            editing.toggle_comment(self)
        elif alt and key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            editing.move_line(self, key == Qt.Key.Key_Down)
        elif ctrl and shift and key == Qt.Key.Key_D:
            editing.duplicate_line(self)
        elif ctrl and shift and key == Qt.Key.Key_K:
            editing.delete_line(self)
        elif text and text in editing.PAIRS and not ctrl:
            self._open_pair(text)
        elif text and text in '}])"' and self._next_char() == text:
            self.moveCursor(QTextCursor.MoveOperation.Right)  # type over the auto-inserted closer
        elif text == "}" and not self.textCursor().block().text().strip():
            self._dedent_close()
        else:
            return False
        return True

    def _next_char(self) -> str:
        cursor = self.textCursor()
        text = cursor.block().text()
        return text[cursor.positionInBlock()] if cursor.positionInBlock() < len(text) else ""

    def _open_pair(self, opener: str) -> None:
        cursor = self.textCursor()
        if cursor.hasSelection():  # surround the selection
            selected = cursor.selectedText()
            cursor.insertText(opener + selected + editing.PAIRS[opener])
            return
        follower = self._next_char()
        if follower and not follower.isspace() and follower not in "}])":
            cursor.insertText(opener)
            return
        cursor.insertText(opener + editing.PAIRS[opener])
        cursor.movePosition(QTextCursor.MoveOperation.Left)
        self.setTextCursor(cursor)

    def _dedent_close(self) -> None:
        cursor = self.textCursor()
        pad = editing.leading_indent(cursor.block().text())
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(pad[: max(0, len(pad) - len(editing.INDENT))] + "}")
        self.setTextCursor(cursor)

    def _tab(self, outdent: bool) -> None:
        cursor = self.textCursor()
        if outdent or cursor.hasSelection():
            editing.indent(self, outdent)
        else:
            cursor.insertText(editing.INDENT)

    # -- mouse: scrubbing, definitions, colours ------------------------------------------------------------
    def word_at(self, position: int) -> tuple[int, str]:
        block = self.document().findBlock(position)
        text, column = block.text(), position - block.position()
        start = column
        while start > 0 and (text[start - 1].isalnum() or text[start - 1] in "_#:."):
            start -= 1
        end = column
        while end < len(text) and (text[end].isalnum() or text[end] in "_#:."):
            end += 1
        return block.position() + start, text[start:end]

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        mods = event.modifiers()
        position = self.cursorForPosition(event.position().toPoint()).position()
        if mods & Qt.KeyboardModifier.AltModifier and self.scrubber.begin(position, event.position().x()):
            return
        if mods & Qt.KeyboardModifier.ControlModifier:
            start, word = self.word_at(position)
            if word and color_of(word) is not None and (word.startswith("#") or self._is_color_token(start)):
                self.color_requested.emit(start, word)
                return
            if word:
                self.definition_requested.emit(word.split("::")[0])
                return
        super().mousePressEvent(event)

    def _is_color_token(self, start: int) -> bool:
        block = self.document().findBlock(start)
        tokens, _ = lex_line(block.text(), max(block.previous().userState(), 0))
        return any(s == start - block.position() and role == "color" for s, _, role in tokens)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self.scrubber.active is not None:
            self.scrubber.move(event.position().x(), event.modifiers())
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self.scrubber.active is not None:
            self.scrubber.end()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self.viewport())
        paint_swatches(self, painter)
        paint_inlays(self, painter, self.analysis, self.theme["editor.inlay.fg"])

    # -- zoom ------------------------------------------------------------------------------------------------
    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom(1 if event.angleDelta().y() > 0 else -1)
            return
        super().wheelEvent(event)

    def zoom(self, steps: int) -> None:
        self.set_font_size(self.font().pointSize() + steps)

    def set_font_size(self, size: int) -> None:
        font = self.font()
        font.setPointSize(max(6, min(40, size)))
        self.setFont(font)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 2)
        self._update_margins()

    def go_to(self, position: int) -> None:
        cursor = self.textCursor()
        cursor.setPosition(max(0, min(position, self.document().characterCount() - 1)))
        self.setTextCursor(cursor)
        self.centerCursor()
        self.setFocus()


__all__ = ["CodeEditor", "QColor"]
