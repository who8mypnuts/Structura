"""The EisenScript code editor (docs/12). A composition root: highlighting, the gutter, bracket matching,
diagnostic squiggles and editing helpers each live in their own module."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QMimeData, QRect, Qt, Signal
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
    QTextOption,
    QWheelEvent,
)
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

from ...core.lang.analysis import Analysis
from ...core.lang.diagnostics import Diagnostic, Severity
from ...core.lang.highlight import lex_line
from ...themes.model import Theme
from ..fonts import CODE_FAMILY, code_font
from ..i18n import tr
from ..theming import qcolor
from .brackets import match_bracket
from .decorations import paint_fold_placeholders, paint_indent_guides
from .folding import Folding
from .gutter import Gutter
from .highlighter import EisenHighlighter, lexer_state
from .inlays import paint_inlays
from .inline_params import InlineParams
from .keys import handle_key
from .minimap import WIDTH as MINIMAP_WIDTH
from .minimap import Minimap
from .multi_cursor import MultiCursor
from .options import EditorOptions
from .scrubber import Scrubber
from .snippet_session import SnippetSession
from .sticky import StickyHeaders
from .swatches import color_of, paint_swatches

DIAG_ROLE = {Severity.ERROR: "diag.error", Severity.WARNING: "diag.warning", Severity.INFO: "diag.info"}


class CodeEditor(QPlainTextEdit):
    cursor_moved = Signal(int, int)  # line, column (1-based)
    definition_requested = Signal(str)  # Ctrl+click / F12 on a rule name
    color_requested = Signal(int, str)  # Ctrl+click on a colour literal: (start position, text)
    analysis_changed = Signal()
    hovered = Signal(int)  # text position under the mouse (no button pressed); -1 when the mouse leaves

    def __init__(self, theme: Theme, parent: QWidget | None = None, shared: CodeEditor | None = None) -> None:
        """``shared``: make this a second view of that editor's document (split view). The views share the
        text, undo history, highlighting and folds; each has its own cursor, scroll position and gutter."""
        super().__init__(parent)
        self.setObjectName("CodeEditor")
        self.setAccessibleName(tr("Script editor"))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.theme = theme
        self.mirrors: list[CodeEditor] = []  # other views of this document (forwarded per-view state)
        if shared is None:
            self.highlighter = EisenHighlighter(self.document(), theme)
            self.gutter = Gutter(self)
            self.folding = Folding(self)
        else:
            self.setDocument(shared.document())
            self.highlighter, self.gutter, self.folding = shared.highlighter, Gutter(self), shared.folding
            shared.mirrors.append(self)
            self.definition_requested.connect(shared.definition_requested)
            self.color_requested.connect(shared.color_requested)
        self.options = EditorOptions()
        self.diagnostics: list[Diagnostic] = []
        self.analysis: Analysis | None = None  # the latest analysis of this text (completion, hover)
        self._selections: dict[str, list[QTextEdit.ExtraSelection]] = {}
        self.blockCountChanged.connect(self._update_margins)
        self.updateRequest.connect(self._update_gutter)
        self.cursorPositionChanged.connect(self._on_cursor)
        self.setMouseTracking(True)
        self.scrubber = Scrubber(self)
        self.snippets = SnippetSession(self)
        self.multi: MultiCursor = MultiCursor(self)
        self.minimap = Minimap(self)
        self.sticky = StickyHeaders(self)
        self.inline_params = InlineParams(self)
        self._press_position = 0
        self._column_anchor: int | None = None
        self.set_theme(theme)
        self.set_font_size(code_font().pointSize())

    # -- theme -------------------------------------------------------------------------------------------
    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        if self.highlighter.theme is not theme:
            self.highlighter.set_theme(theme)  # shared by every view: rehighlight once
        self.gutter.colors = {
            "fg": qcolor(theme["editor.line.number"]),
            "active": qcolor(theme["editor.line.number.active"]),
            "bg": qcolor(theme["editor.bg"]),
            "fold": qcolor(theme["editor.fold.marker"]),
        }
        self.set_diagnostics(self.diagnostics)
        self._on_cursor()
        self.minimap.rebuild()
        for view in self.mirrors:
            view.set_theme(theme)

    def set_analysis(self, analysis: Analysis | None) -> None:
        """The latest analysis of this text (completion, hover, inlays), for every view."""
        self.analysis = analysis
        self.viewport().update()
        self.analysis_changed.emit()
        for view in self.mirrors:
            view.set_analysis(analysis)

    # -- view options ----------------------------------------------------------------------------------------
    def set_options(self, options: EditorOptions) -> None:
        self.options = options
        wrap = QPlainTextEdit.LineWrapMode.WidgetWidth if options.word_wrap else QPlainTextEdit.LineWrapMode.NoWrap
        self.setLineWrapMode(wrap)
        text_option = self.document().defaultTextOption()
        flags = text_option.flags()
        whitespace = QTextOption.Flag.ShowTabsAndSpaces
        text_option.setFlags(flags | whitespace if options.show_whitespace else flags & ~whitespace)
        self.document().setDefaultTextOption(text_option)
        self.highlighter.set_rainbow(options.rainbow_brackets)
        self.set_font_size(options.code_size)
        self.sticky.refresh()
        self.viewport().update()
        for view in self.mirrors:
            view.set_options(options)

    # -- layout & gutter -----------------------------------------------------------------------------------
    def _update_margins(self) -> None:
        right = MINIMAP_WIDTH if self.options.minimap else 0
        self.setViewportMargins(self.gutter.width_needed(), 0, right, 0)
        self._place_overlays()

    def _place_overlays(self) -> None:
        r, viewport = self.contentsRect(), self.viewport().geometry()
        self.gutter.setGeometry(QRect(r.left(), r.top(), self.gutter.width_needed(), r.height()))
        self.minimap.setGeometry(QRect(viewport.right() + 1, viewport.top(), MINIMAP_WIDTH, viewport.height()))
        self.minimap.setVisible(self.options.minimap)

    def _update_gutter(self, rect: QRect, dy: int) -> None:
        if dy:
            self.gutter.scroll(0, dy)
        else:
            self.gutter.update(0, rect.y(), self.gutter.width(), rect.height())

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._place_overlays()
        self.sticky.refresh()

    # -- extra selections (current line, brackets, diagnostics) ----------------------------------------------
    def set_selections(self, layer: str, selections: list[QTextEdit.ExtraSelection]) -> None:
        self._selections[layer] = selections
        order = ("line", "find", "brackets", "multi", "diagnostics")
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
        for view in self.mirrors:
            view.set_diagnostics(diagnostics)

    def diagnostic_at(self, pos: int) -> Diagnostic | None:
        for d in self.diagnostics:
            if d.span is not None and d.span.start <= pos <= max(d.span.end, d.span.start + 1):
                return d
        return None

    # -- typing aids (key bindings in keys.py) ---------------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if not handle_key(self, event):
            super().keyPressEvent(event)

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
        alt, ctrl = mods & Qt.KeyboardModifier.AltModifier, mods & Qt.KeyboardModifier.ControlModifier
        self._press_position = position
        if alt and mods & Qt.KeyboardModifier.ShiftModifier:
            self._column_anchor = position  # column selection
            return
        if alt and ctrl:
            self.multi.add_at(position)
            return
        if alt:
            if not self.scrubber.begin(position, event.position().x()):
                self.multi.add_at(position)
            return
        if not ctrl:
            self.multi.clear()
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
        tokens, _ = lex_line(block.text(), lexer_state(block.previous().userState()))
        return any(s == start - block.position() and role == "color" for s, _, role in tokens)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._column_anchor is not None:
            position = self.cursorForPosition(event.position().toPoint()).position()
            self.multi.column_select(self._column_anchor, position)
            return
        if self.scrubber.active is not None:
            self.scrubber.move(event.position().x(), event.modifiers())
            return
        if event.buttons() == Qt.MouseButton.NoButton:
            self.hovered.emit(self.cursorForPosition(event.position().toPoint()).position())
        super().mouseMoveEvent(event)

    def leaveEvent(self, event: QEvent) -> None:  # noqa: N802
        self.hovered.emit(-1)
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._column_anchor is not None:
            self._column_anchor = None
            return
        if self.scrubber.active is not None:
            if not self.scrubber.end():  # an Alt+click on a number: add a cursor there
                self.multi.add_at(self._press_position)
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self.viewport())
        if self.options.indent_guides:
            paint_indent_guides(self, painter, qcolor(self.theme["editor.indent.guide"]))
        folded = self.folding.folded_lines()
        paint_fold_placeholders(
            self, painter, folded, self.gutter.colors["fold"], qcolor(self.theme["editor.inlay.bg"])
        )
        paint_swatches(self, painter)
        for cursor in self.multi.extra:  # the extra carets
            rect = self.cursorRect(cursor)
            painter.fillRect(QRect(rect.x(), rect.y(), 2, rect.height()), qcolor(self.theme["editor.cursor"]))
        paint_inlays(self, painter, self.analysis, self.theme["editor.inlay.fg"])

    def canInsertFromMimeData(self, source: QMimeData) -> bool:  # noqa: N802
        """Dropped files are opened by the window, not pasted as their path."""
        if source.hasUrls() and any(url.isLocalFile() for url in source.urls()):
            return False
        return super().canInsertFromMimeData(source)

    # -- zoom ------------------------------------------------------------------------------------------------
    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom(1 if event.angleDelta().y() > 0 else -1)
            return
        super().wheelEvent(event)

    def zoom(self, steps: int) -> None:
        self.set_font_size(self.font().pointSize() + steps)

    def set_font_size(self, size: int) -> None:
        size = max(6, min(40, size))
        # A widget style sheet outranks the application's (whose QWidget rule sets the UI font), so the code
        # font and this editor's zoom survive theme changes; setFont keeps metrics right before polishing.
        self.setStyleSheet(f'QPlainTextEdit#CodeEditor {{ font-family: "{CODE_FAMILY}"; font-size: {size}pt; }}')
        font = code_font(size)
        self.setFont(font)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 2)
        self._update_margins()

    def go_to(self, position: int) -> None:
        cursor = self.textCursor()
        cursor.setPosition(max(0, min(position, self.document().characterCount() - 1)))
        self.folding.reveal(cursor.blockNumber())
        self.setTextCursor(cursor)
        self.centerCursor()
        self.setFocus()


__all__ = ["CodeEditor", "QColor"]
