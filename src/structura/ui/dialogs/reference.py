"""The language reference browser (F1, docs/12 §2.2): the generated reference (core.lang.reference) in a
themed QTextBrowser, scrolled to the symbol under the cursor. Non-modal; one instance is reused."""

from __future__ import annotations

from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QDialog, QLineEdit, QTextBrowser, QVBoxLayout, QWidget

from ...core.lang.reference import to_html
from ...themes.model import Theme


class ReferenceBrowser(QDialog):
    def __init__(self, theme: Theme, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("EisenScript reference")
        self.resize(640, 720)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Find in the reference (Enter for the next match)")
        self.search.returnPressed.connect(self.find_next)
        self.browser = QTextBrowser()
        self.browser.setOpenLinks(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self.search)
        layout.addWidget(self.browser, 1)
        self.set_theme(theme)

    def set_theme(self, theme: Theme) -> None:
        css = (f"code {{ color: {theme['syntax.keyword'][:7]}; }} a {{ color: {theme['ui.accent'][:7]}; }}"
               f" h2 {{ color: {theme['ui.fg'][:7]}; margin-top: 18px; }}")  # fmt: skip
        self.browser.document().setDefaultStyleSheet(css)
        self.browser.setHtml(to_html())

    def show_anchor(self, anchor: str | None) -> None:
        if anchor:
            self.browser.scrollToAnchor(anchor)
        self.show()
        self.raise_()
        self.activateWindow()

    def find_next(self) -> None:
        needle = self.search.text()
        if needle and not self.browser.find(needle):
            self.browser.moveCursor(self.browser.textCursor().MoveOperation.Start)  # wrap around
            self.browser.find(needle, QTextDocument.FindFlag(0))
