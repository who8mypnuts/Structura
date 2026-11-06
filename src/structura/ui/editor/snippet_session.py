"""Snippet sessions (docs/12 §2.3): after inserting a snippet with tab stops, Tab / Shift+Tab visit them,
Esc ends the session, and leaving a stop copies its text to the stop's mirrors. Stops are pairs of
QTextCursors, so they follow edits made while the session runs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QKeyEvent, QTextCursor

from ...core.lang.snippet_syntax import expand

if TYPE_CHECKING:
    from .code_editor import CodeEditor


class _Marker:
    """One stop: a start that stays before text typed at it and an end that grows with it."""

    def __init__(self, editor: CodeEditor, index: int, start: int, end: int) -> None:
        self.index = index
        self.start, self.end = QTextCursor(editor.document()), QTextCursor(editor.document())
        self.start.setPosition(start)
        self.end.setPosition(end)
        self.start.setKeepPositionOnInsert(True)

    def _selection(self) -> QTextCursor:
        """A fresh cursor over the stop (copying ``start`` would copy its anchor, which drifts on insert)."""
        cursor = QTextCursor(self.start.document())
        cursor.setPosition(self.start.position())
        cursor.setPosition(self.end.position(), QTextCursor.MoveMode.KeepAnchor)
        return cursor

    def text(self) -> str:
        return self._selection().selectedText()

    def replace(self, text: str) -> None:
        self._selection().insertText(text)


class SnippetSession(QObject):
    def __init__(self, editor: CodeEditor) -> None:
        super().__init__(editor)
        self.editor = editor
        self.markers: list[_Marker] = []
        self.current = -1
        editor.installEventFilter(self)

    @property
    def active(self) -> bool:
        return self.current >= 0

    def insert(self, snippet: str, start: int, end: int) -> None:
        """Replace [start, end) with the snippet and select its first stop (if it has any)."""
        text, stops = expand(snippet)
        cursor = QTextCursor(self.editor.document())
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(text)
        self.editor.setTextCursor(cursor)
        self.markers = [_Marker(self.editor, s.index, start + s.start, start + s.end) for s in stops]
        self.current = -1
        if self.markers:
            self._visit(0)

    def _first_of_each_index(self) -> list[int]:
        """Marker positions visited by Tab: the first marker of each stop index (the rest are mirrors)."""
        seen: set[int] = set()
        visits = []
        for position, marker in enumerate(self.markers):
            if marker.index not in seen:
                seen.add(marker.index)
                visits.append(position)
        return visits

    def _visit(self, order: int) -> None:
        visits = self._first_of_each_index()
        if not 0 <= order < len(visits):
            self.end()
            return
        self.current = order
        marker = self.markers[visits[order]]
        cursor = self.editor.textCursor()
        cursor.setPosition(marker.start.position())
        cursor.setPosition(marker.end.position(), QTextCursor.MoveMode.KeepAnchor)
        self.editor.setTextCursor(cursor)
        if marker.index == 0:
            self.end()

    def _mirror(self) -> None:
        if not self.active:
            return
        source = self.markers[self._first_of_each_index()[self.current]]
        text = source.text()
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()
        for marker in self.markers:
            if marker is not source and marker.index == source.index and marker.text() != text:
                marker.replace(text)
        cursor.endEditBlock()

    def step(self, delta: int) -> None:
        self._mirror()
        self._visit(max(0, self.current + delta))

    def end(self) -> None:
        self.current = -1
        self.markers = []

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if not self.active or not isinstance(event, QKeyEvent) or event.type() != QEvent.Type.KeyPress:
            return False
        if event.key() == Qt.Key.Key_Tab and not event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.step(1)
            return True
        if event.key() == Qt.Key.Key_Backtab:
            self.step(-1)
            return True
        if event.key() == Qt.Key.Key_Escape:
            self._mirror()
            self.end()
            return True
        return False


def insert_snippet(editor: CodeEditor, snippet: str, start: int | None = None, end: int | None = None) -> None:
    cursor = editor.textCursor()
    begin = cursor.selectionStart() if start is None else start
    finish = cursor.selectionEnd() if end is None else end
    editor.snippets.insert(snippet, begin, finish)
