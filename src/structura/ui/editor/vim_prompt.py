"""The Vim command line (docs/12 §2.1, P2): ':' commands and '/' or '?' searches, typed in a one-line field at
the bottom of the editor. Enter runs it, Escape cancels; the editor gets the focus back either way."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QLineEdit, QPlainTextEdit

from ..i18n import tr


class VimPrompt(QLineEdit):
    def __init__(self, editor: QPlainTextEdit, run: Callable[[str, str], None]) -> None:
        super().__init__(editor)
        self.editor, self.run, self.kind = editor, run, ":"
        self.setObjectName("VimPrompt")
        self.setAccessibleName(tr("Vim command line"))
        self.installEventFilter(self)
        self.hide()

    def open(self, kind: str) -> None:
        self.kind = kind
        self.setPlaceholderText(kind)
        self.setText("")
        height = self.sizeHint().height()
        viewport = self.editor.viewport().geometry()
        self.setGeometry(viewport.left(), viewport.bottom() - height, viewport.width(), height)
        self.show()
        self.raise_()
        self.setFocus()

    def _accept(self) -> None:
        text = self.text()
        self._close()
        if text:
            self.run(self.kind, text)

    def _close(self) -> None:
        self.hide()
        self.editor.setFocus()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if isinstance(event, QKeyEvent) and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self._close()
                return True
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):  # (QLineEdit would pass it to the editor)
                self._accept()
                return True
        return False
