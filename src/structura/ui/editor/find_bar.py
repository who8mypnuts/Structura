"""Find / replace bar (docs/12 §2.1): regex, case, whole word, match count, replace all as one undo step."""

from __future__ import annotations

import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget

from ..i18n import tr
from ..theming import qcolor
from .code_editor import CodeEditor

MAX_MATCHES = 5000


class FindBar(QWidget):
    closed = Signal()

    def __init__(self, editor: CodeEditor) -> None:
        super().__init__(editor.parentWidget())
        self.editor = editor
        self.find_edit, self.replace_edit = QLineEdit(), QLineEdit()
        self.find_edit.setAccessibleName(tr("Find"))
        self.replace_edit.setAccessibleName(tr("Replace with"))
        self.find_edit.setPlaceholderText("Find")
        self.replace_edit.setPlaceholderText("Replace")
        self.case, self.regex, self.word = QCheckBox("Aa"), QCheckBox(".*"), QCheckBox("W")
        self.count = QLabel("")
        self.count.setObjectName("Muted")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        for widget in (self.find_edit, self.case, self.word, self.regex, self.count, self.replace_edit):
            layout.addWidget(widget)
        for title, slot in (("↑", self.previous), ("↓", self.next), ("Replace", self.replace_one),
                            ("All", self.replace_all), ("✕", self.close_bar)):  # fmt: skip
            button = QPushButton(title)
            button.clicked.connect(slot)
            layout.addWidget(button)
        self.find_edit.textChanged.connect(self.refresh)
        self.find_edit.returnPressed.connect(self.next)
        for box in (self.case, self.regex, self.word):
            box.toggled.connect(self.refresh)
        self.hide()

    def pattern(self) -> re.Pattern[str] | None:
        text = self.find_edit.text()
        if not text:
            return None
        source = text if self.regex.isChecked() else re.escape(text)
        if self.word.isChecked():
            source = rf"\b{source}\b"
        try:
            return re.compile(source, 0 if self.case.isChecked() else re.IGNORECASE)
        except re.error:
            return None

    def matches(self) -> list[tuple[int, int]]:
        pattern = self.pattern()
        if pattern is None:
            return []
        found = []
        for m in pattern.finditer(self.editor.toPlainText()):
            if m.end() > m.start():
                found.append((m.start(), m.end()))
            if len(found) >= MAX_MATCHES:
                break
        return found

    def open(self, replace: bool = False) -> None:
        self.show()
        selected = self.editor.textCursor().selectedText()
        if selected and "\u2029" not in selected:
            self.find_edit.setText(selected)
        (self.replace_edit if replace else self.find_edit).setFocus()
        self.find_edit.selectAll()
        self.refresh()

    def close_bar(self) -> None:
        self.hide()
        self.editor.set_selections("find", [])
        self.editor.setFocus()
        self.closed.emit()

    def refresh(self) -> None:
        found = self.matches()
        fmt = QTextCharFormat()
        fmt.setBackground(qcolor(self.editor.theme["editor.find.match"]))
        self.editor.set_selections("find", [self.editor.selection_for(a, b, fmt) for a, b in found])
        self.count.setText(f"{len(found)} match{'es' if len(found) != 1 else ''}" if self.find_edit.text() else "")

    def _select(self, span: tuple[int, int]) -> None:
        cursor = self.editor.textCursor()
        cursor.setPosition(span[0])
        cursor.setPosition(span[1], QTextCursor.MoveMode.KeepAnchor)
        self.editor.setTextCursor(cursor)

    def next(self) -> None:
        found = self.matches()
        if found:
            pos = self.editor.textCursor().selectionEnd()
            self._select(next((m for m in found if m[0] >= pos), found[0]))

    def previous(self) -> None:
        found = self.matches()
        if found:
            pos = self.editor.textCursor().selectionStart()
            self._select(next((m for m in reversed(found) if m[1] <= pos), found[-1]))

    def replace_one(self) -> None:
        cursor = self.editor.textCursor()
        pattern = self.pattern()
        if pattern is not None and cursor.hasSelection() and pattern.fullmatch(cursor.selectedText()):
            cursor.insertText(pattern.sub(self.replace_edit.text(), cursor.selectedText()))
        self.next()

    def replace_all(self) -> None:
        pattern = self.pattern()
        if pattern is None:
            return
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()  # one undo step
        for start, end in reversed(self.matches()):
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            cursor.insertText(pattern.sub(self.replace_edit.text(), cursor.selectedText()))
        cursor.endEditBlock()
        self.refresh()

    def keyPressEvent(self, event: object) -> None:  # noqa: N802
        if getattr(event, "key", lambda: None)() == Qt.Key.Key_Escape:
            self.close_bar()
            return
        super().keyPressEvent(event)  # type: ignore[arg-type]
