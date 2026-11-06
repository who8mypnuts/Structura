"""Peek definition (Alt+F12, docs/12 §2.2): the definitions of the rule under the cursor in a read-only
popup at the cursor. An ambiguous rule shows every alternative. Double-click jumps there; Esc closes."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from ...core.lang.source import Span
from .code_editor import CodeEditor

WIDTH, MAX_HEIGHT = 560, 320


def rule_spans(editor: CodeEditor, name: str) -> list[Span]:
    analysis = editor.analysis
    if analysis is None:
        return []
    return [r.span for r in analysis.rules if r.name == name.lower()]


class PeekPopup(QFrame):
    def __init__(self, editor: CodeEditor, name: str, spans: list[Span]) -> None:
        super().__init__(editor, Qt.WindowType.Popup)
        self.setObjectName("PeekPopup")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.editor, self.spans = editor, spans
        text = editor.toPlainText()
        self.view = CodeEditor(editor.theme)
        self.view.setPlainText("\n\n".join(text[s.start : s.end] for s in spans))
        self.view.setReadOnly(True)
        self.view.set_options(replace(editor.options, minimap=False, sticky_scroll=False, breadcrumbs=False))
        self.view.viewport().installEventFilter(self)
        count = f"{len(spans)} definitions" if len(spans) > 1 else "1 definition"
        title = QLabel(f"rule {name} · {count} · double-click to go there")
        title.setObjectName("Muted")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 6)
        layout.addWidget(title)
        layout.addWidget(self.view, 1)
        lines = sum(text[s.start : s.end].count("\n") + 2 for s in spans)
        self.resize(WIDTH, min(MAX_HEIGHT, 40 + lines * editor.fontMetrics().height()))

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if isinstance(event, QMouseEvent) and event.type() == QEvent.Type.MouseButtonDblClick:
            self._jump()
            return True
        return False

    def _jump(self) -> None:
        """Go to the alternative that was double-clicked (the peek text joins them with a blank line)."""
        line = self.view.textCursor().blockNumber()
        text = self.editor.toPlainText()
        for span in self.spans:
            lines = text[span.start : span.end].count("\n") + 2
            if line < lines:
                self.close()
                self.editor.go_to(span.start)
                return
            line -= lines
        self.close()


def peek_definition(editor: CodeEditor, name: str) -> bool:
    spans = rule_spans(editor, name)
    if not spans:
        return False
    popup = PeekPopup(editor, name, spans)
    point = editor.viewport().mapToGlobal(editor.cursorRect().bottomLeft())
    popup.move(point)
    popup.show()
    return True
