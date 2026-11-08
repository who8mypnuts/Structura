"""Quick-fix menu (Ctrl+., docs/12 §2.2): the fixes of the diagnostics at the cursor and the refactorings
there, each applied as one undo step. They come from core.lang.fixes and core.lang.restructure."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QMenu, QToolTip

from ...core.lang.diagnostics import Diagnostic
from ...core.lang.fixes import QuickFix, quick_fixes
from ...core.lang.restructure import refactorings_at

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
    """Ctrl+.: the fixes of the problems at the cursor, then the refactorings that apply there."""
    position = editor.textCursor().position()
    _menu(editor, [fixes_at(editor, position), refactorings_at(editor.toPlainText(), position)], "No quick fixes here")


def show_refactorings(editor: CodeEditor) -> None:
    position = editor.textCursor().position()
    _menu(editor, [refactorings_at(editor.toPlainText(), position)], "No refactorings here")


def _menu(editor: CodeEditor, groups: list[list[QuickFix]], empty: str) -> None:
    point = editor.viewport().mapToGlobal(editor.cursorRect().bottomLeft())
    groups = [g for g in groups if g]
    if not groups:
        QToolTip.showText(point, empty, editor)
        return
    menu = QMenu(editor)
    for k, group in enumerate(groups):
        if k:
            menu.addSeparator()
        for fix in group:
            menu.addAction(fix.title).triggered.connect(lambda _c=False, f=fix: apply_fix(editor, f))
    run_menu(menu, point)


def run_menu(menu: QMenu, point: QPoint) -> None:
    menu.exec(point)  # modal (tests replace this function)
