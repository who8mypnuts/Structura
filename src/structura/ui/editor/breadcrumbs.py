"""Breadcrumbs above the editor (docs/12 §2.2): 'file › rule' for the rule containing the cursor; the rule
segment opens a menu of every rule in the script to jump to it."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QHBoxLayout, QLabel, QMenu, QToolButton, QWidget

from ...core.lang.analysis import Analysis, RuleSymbol

if TYPE_CHECKING:
    from .code_editor import CodeEditor

SEPARATOR = "›"


def rule_at(analysis: Analysis | None, position: int) -> RuleSymbol | None:
    if analysis is None:
        return None
    return next((r for r in analysis.rules if r.span.start <= position <= r.span.end), None)


class Breadcrumbs(QWidget):
    def __init__(self, editor: CodeEditor, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Breadcrumbs")
        self.editor = editor
        self.file = QLabel("")
        self.file.setObjectName("Muted")
        self.rule = QToolButton()
        self.rule.setObjectName("BreadcrumbRule")
        self.rule.setAutoRaise(True)
        self.rule.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.rule.setMenu(QMenu(self.rule))
        self.rule.menu().aboutToShow.connect(self._fill_menu)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 1, 8, 1)
        layout.setSpacing(4)
        layout.addWidget(self.file)
        layout.addWidget(self.rule)
        layout.addStretch(1)
        editor.cursorPositionChanged.connect(self.refresh)
        editor.analysis_changed.connect(self.refresh)

    def set_file(self, name: str) -> None:
        self.file.setText(f"{name} {SEPARATOR}")
        self.refresh()

    def refresh(self) -> None:
        rule = rule_at(self.editor.analysis, self.editor.textCursor().position())
        self.rule.setText(f"rule {rule.name}" if rule else "top level")

    def _fill_menu(self) -> None:
        menu = self.rule.menu()
        menu.clear()
        analysis = self.editor.analysis
        for r in analysis.rules if analysis else ():
            line = self.editor.document().findBlock(r.span.start).blockNumber() + 1
            menu.addAction(f"rule {r.name}   (line {line})").triggered.connect(
                lambda _c=False, at=r.span.start: self.editor.go_to(at)
            )
