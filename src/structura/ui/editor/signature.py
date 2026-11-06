"""Signature help (docs/12 §3): a label above the cursor while typing a v2 function call, with the current
argument in bold. Refreshed after every key press (deferred so the edit has been applied)."""

from __future__ import annotations

import html
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QObject, QTimer
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QLabel

from ...core.lang.signatures import Signature, signature_at

if TYPE_CHECKING:
    from .code_editor import CodeEditor


def signature_html(sig: Signature) -> str:
    params = [f"<b>{html.escape(p)}</b>" if i == sig.active else html.escape(p) for i, p in enumerate(sig.params)]
    return f"<code>{sig.name}({', '.join(params)})</code><br/>{html.escape(sig.doc)}"


class SignatureHelp(QObject):
    def __init__(self, editor: CodeEditor) -> None:
        super().__init__(editor)
        self.editor = editor
        self.label = QLabel(editor)
        self.label.setObjectName("signatureHelp")
        self.label.setAutoFillBackground(True)
        self.label.setBackgroundRole(QPalette.ColorRole.ToolTipBase)
        self.label.setForegroundRole(QPalette.ColorRole.ToolTipText)
        self.label.setMargin(4)
        self.label.hide()
        editor.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.KeyPress:
            QTimer.singleShot(0, self.refresh)
        elif event.type() == QEvent.Type.FocusOut:
            self.label.hide()
        return False

    def refresh(self) -> None:
        cursor = self.editor.textCursor()
        sig = signature_at(self.editor.toPlainText(), cursor.position())
        if sig is None:
            self.label.hide()
            return
        self.label.setText(signature_html(sig))
        self.label.adjustSize()
        rect = self.editor.cursorRect(cursor)
        origin = self.editor.viewport().mapTo(self.editor, rect.topLeft())
        x = origin.x() + self.editor.viewportMargins().left()
        self.label.move(x, max(0, origin.y() - self.label.height() - 2))
        self.label.show()
        self.label.raise_()
