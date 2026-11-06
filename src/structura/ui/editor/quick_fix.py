"""Quick-fix menu (Ctrl+., docs/12 §2.2): the fixes of the diagnostics at the cursor, applied as one undo
step. The fixes themselves come from core.lang.fixes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QMenu, QToolTip

from ...core.lang.diagnostics import Diagnostic
from ...core.lang.fixes import QuickFix, quick_fixes

if TYPE_CHECKING:
    from .code_editor import CodeEditor


def diagnostics_at(editor: CodeEditor, position: int) -> list[Diagnostic]:
    """Diagnostics under the cursor, or else on the cursor's line."""
    spans = [d for d in editor.diagnostics if d.span is not None]
    under = [d for d in spans if d.span and d.span.start <= position <= max(d.span.end, d.span.start + 1)]
    if under:
        return under
    block = editor.document().findBlock(position)
    start, end = block.position(), block.position() + block.length()
    return [d for d in spans if d.span and start <= d.span.start < end]


def fixes_at(editor: CodeEditor, position: int) -> list[QuickFix]:
    return quick_fixes(editor.toPlainText(), diagnostics_at(editor, position))


def apply_fix(editor: CodeEditor, fix: QuickFix) -> None:
    cursor = QTextCursor(editor.document())
    cursor.beginEditBlock()
    for edit in sorted(fix.edits, key=lambda e: e.start, reverse=True):
        cursor.setPosition(edit.start)
        cursor.setPosition(edit.end, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(edit.text)
    cursor.endEditBlock()


def show_quick_fixes(editor: CodeEditor) -> None:
    fixes = fixes_at(editor, editor.textCursor().position())
    rect = editor.cursorRect()
    point = editor.viewport().mapToGlobal(rect.bottomLeft())
    if not fixes:
        QToolTip.showText(point, "No quick fixes here", editor)
        return
    menu = QMenu(editor)
    for fix in fixes:
        menu.addAction(fix.title).triggered.connect(lambda _c=False, f=fix: apply_fix(editor, f))
    menu.exec(point)
