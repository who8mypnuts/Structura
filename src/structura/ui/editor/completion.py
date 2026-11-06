"""Completion popup and hover documentation (docs/12 §3). Both attach to a CodeEditor through an event
filter, so the editor class stays a small composition root. Items come from core.lang.assist."""

from __future__ import annotations

import html
import re

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QKeyEvent, QTextCursor
from PySide6.QtWidgets import QFrame, QLabel, QListWidget, QListWidgetItem, QToolTip, QVBoxLayout

from ...core.lang.assist import CompletionItem, Completions, complete, hover
from ...core.lang.snippet_syntax import has_stops
from ..i18n import tr
from .code_editor import CodeEditor
from .snippet_session import insert_snippet

ICONS = {"keyword": "⌘", "operator": "↻", "modifier": "≡", "primitive": "◼", "rule": "ƒ", "color": "●",
         "set": "⚙", "raytracer": "☀", "snippet": "✂", "preprocessor": "#"}  # fmt: skip
WORD_CHAR = re.compile(r"[A-Za-z0-9_:#.\-]")
MAX_ITEMS = 200


def markdown_to_html(text: str) -> str:
    escaped = html.escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped).replace("\n", "<br>")


class CompletionPopup(QFrame):
    def __init__(self, editor: CodeEditor) -> None:
        super().__init__(editor)
        self.setObjectName("CommandPalette")
        self.list, self.doc = QListWidget(), QLabel()
        self.list.setAccessibleName(tr("Completions"))
        self.doc.setWordWrap(True)
        self.doc.setObjectName("Muted")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.list)
        layout.addWidget(self.doc)
        self.list.currentItemChanged.connect(self._describe)
        self.items: list[CompletionItem] = []
        self.hide()

    def show_items(self, items: tuple[CompletionItem, ...], x: int, y: int) -> None:
        self.items = list(items[:MAX_ITEMS])
        self.list.clear()
        for item in self.items:
            row = QListWidgetItem(f"{ICONS.get(item.kind, '·')}  {item.label}    {item.detail}")
            self.list.addItem(row)
        self.list.setCurrentRow(0)
        self.setGeometry(x, y, 420, min(320, 60 + 22 * len(self.items)))
        self.show()
        self.raise_()

    def current(self) -> CompletionItem | None:
        row = self.list.currentRow()
        return self.items[row] if 0 <= row < len(self.items) else None

    def move_selection(self, delta: int) -> None:
        self.list.setCurrentRow(max(0, min(self.list.count() - 1, self.list.currentRow() + delta)))

    def _describe(self) -> None:
        item = self.current()
        self.doc.setText(markdown_to_html(f"**{item.label}** {item.detail}\n{item.doc}") if item else "")


class CompletionController(QObject):
    """Shows completions while typing (or on Ctrl+Space) and documentation on hover."""

    def __init__(self, editor: CodeEditor) -> None:
        super().__init__(editor)
        self.editor = editor
        self.popup = CompletionPopup(editor)
        self.completions: Completions | None = None
        editor.installEventFilter(self)
        editor.viewport().installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if isinstance(event, QKeyEvent) and event.type() == QEvent.Type.KeyPress and watched is self.editor:
            return self._key(event)
        if event.type() == QEvent.Type.ToolTip and watched is self.editor.viewport():
            return self._hover()
        return False

    def _key(self, event: QKeyEvent) -> bool:
        key = event.key()
        if self.popup.isVisible():
            if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                self.popup.move_selection(-1 if key == Qt.Key.Key_Up else 1)
                return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab):
                self.accept()
                return True
            if key == Qt.Key.Key_Escape:
                self.popup.hide()
                return True
        ctrl = event.modifiers() & Qt.KeyboardModifier.ControlModifier
        if ctrl and key == Qt.Key.Key_Space:
            self.trigger(force=True)
            return True
        if event.text() and WORD_CHAR.fullmatch(event.text()) and not ctrl:
            self.editor.keyPressEvent(event)  # type the character first, then refresh the list
            self.trigger(force=False)
            return True
        if self.popup.isVisible() and key not in (Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Alt):
            self.popup.hide()
        return False

    def trigger(self, force: bool) -> None:
        cursor = self.editor.textCursor()
        result = complete(self.editor.toPlainText(), cursor.position(), self.editor.analysis)
        self.completions = result
        exact = len(result.items) == 1 and result.items[0].label == result.prefix
        if not result.items or exact or (not force and not result.prefix):
            self.popup.hide()
            return
        rect = self.editor.cursorRect(cursor)
        origin = self.editor.viewport().mapTo(self.editor, rect.bottomLeft())
        self.popup.show_items(result.items, origin.x() + self.editor.viewportMargins().left(), origin.y() + 4)

    def accept(self) -> None:
        item, result = self.popup.current(), self.completions
        self.popup.hide()
        if item is None or result is None:
            return
        if has_stops(item.text):
            insert_snippet(self.editor, item.text, result.start, self.editor.textCursor().position())
            return
        cursor = self.editor.textCursor()
        cursor.setPosition(result.start, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(item.text)
        self.editor.setTextCursor(cursor)

    def _hover(self) -> bool:
        editor = self.editor
        pos = editor.viewport().mapFromGlobal(editor.cursor().pos())
        offset = editor.cursorForPosition(pos).position()
        diagnostic = editor.diagnostic_at(offset)
        text = (
            f"**{diagnostic.code}** {diagnostic.message}"
            if diagnostic
            else hover(editor.toPlainText(), offset, editor.analysis)
        )
        if text:
            QToolTip.showText(editor.cursor().pos(), markdown_to_html(text), editor)
        else:
            QToolTip.hideText()
        return True
