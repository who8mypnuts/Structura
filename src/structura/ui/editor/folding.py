"""Code folding for the CodeEditor (docs/12 §2.1): fold ranges come from core.lang.folding; folded ranges
hide their body blocks. A folded range is remembered by a QTextCursor on its header line, so it follows
edits above it. Moving the cursor into hidden text unfolds around it."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QTextCursor

from ...core.lang.folding import FoldRange, fold_ranges

if TYPE_CHECKING:
    from .code_editor import CodeEditor

REFRESH_MS = 120


class Folding(QObject):
    def __init__(self, editor: CodeEditor) -> None:
        super().__init__(editor)
        self.editor = editor
        self.ranges: dict[int, FoldRange] = {}  # header line -> range
        self._folded: list[QTextCursor] = []
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(REFRESH_MS)
        self._timer.timeout.connect(self.refresh)
        editor.document().contentsChanged.connect(self._timer.start)
        editor.cursorPositionChanged.connect(self._reveal_cursor)

    # -- state -------------------------------------------------------------------------------------------
    def folded_lines(self) -> set[int]:
        return {c.blockNumber() for c in self._folded}

    def is_folded(self, line: int) -> bool:
        return line in self.folded_lines()

    def refresh(self) -> None:
        """Recompute ranges after an edit; folds whose range disappeared are opened."""
        self.ranges = {r.start: r for r in fold_ranges(self.editor.toPlainText())}
        self._folded = [c for c in self._folded if c.blockNumber() in self.ranges]
        self._apply()

    def range_at(self, line: int) -> FoldRange | None:
        """The innermost range whose header is ``line`` or whose body contains it."""
        self._ensure_fresh()
        around = [r for r in self.ranges.values() if r.start <= line <= r.end]
        return max(around, key=lambda r: r.start) if around else None

    # -- commands ----------------------------------------------------------------------------------------
    def _ensure_fresh(self) -> None:
        if self._timer.isActive() or not self.ranges:
            self._timer.stop()
            self.refresh()

    def fold_at(self, line: int, fold: bool) -> None:
        """Fold (or unfold) the innermost range around ``line``; the cursor moves to its header."""
        found = self.range_at(line)
        if found is None or self.is_folded(found.start) == fold:
            return
        if fold:
            self.editor.setTextCursor(self._cursor_at(found.start))
        self.toggle(found.start)

    def toggle(self, line: int) -> None:
        self._ensure_fresh()
        if self.is_folded(line):
            self._folded = [c for c in self._folded if c.blockNumber() != line]
        elif line in self.ranges:
            self._folded.append(self._cursor_at(line))
        else:
            return
        self._apply()

    def fold_all(self) -> None:
        self._ensure_fresh()
        self._folded = [self._cursor_at(line) for line in self.ranges]
        self._apply()

    def unfold_all(self) -> None:
        self._folded = []
        self._apply()

    def reveal(self, line: int) -> None:
        """Unfold every folded range that hides ``line``."""
        if not self._folded:
            return
        hidden_by = [c for c in self._folded if self._hides(c.blockNumber(), line)]
        if hidden_by:
            self._folded = [c for c in self._folded if c not in hidden_by]
            self._apply()

    # -- internals ---------------------------------------------------------------------------------------
    def _cursor_at(self, line: int) -> QTextCursor:
        return QTextCursor(self.editor.document().findBlockByNumber(line))

    def _hides(self, header: int, line: int) -> bool:
        fold = self.ranges.get(header)
        return fold is not None and fold.start < line <= fold.end

    def _reveal_cursor(self) -> None:
        if not self.editor.textCursor().block().isVisible():
            self.reveal(self.editor.textCursor().blockNumber())

    def _apply(self) -> None:
        hidden: set[int] = set()
        for header in self.folded_lines():
            fold = self.ranges[header]
            hidden.update(range(fold.start + 1, fold.end + 1))
        document = self.editor.document()
        block = document.begin()
        changed = False
        while block.isValid():
            visible = block.blockNumber() not in hidden
            if block.isVisible() != visible:
                block.setVisible(visible)
                changed = True
            block = block.next()
        if changed:
            document.markContentsDirty(0, document.characterCount())
            self.editor.viewport().update()
            self.editor.minimap.rebuild()
        self.editor.gutter.update()
