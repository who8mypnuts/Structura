"""Lexical highlighting through core.lang.highlight.lex_line (one lexer, no regexes here; docs/12 §1)."""

from __future__ import annotations

from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QTextDocument

from ...core.lang.highlight import lex_line
from ...themes.model import Theme
from ..theming import syntax_format


class EisenHighlighter(QSyntaxHighlighter):
    """Lexical colours per block, refined by the latest analysis (defined / undefined / unused rules)."""

    def __init__(self, document: QTextDocument, theme: Theme) -> None:
        super().__init__(document)
        self._formats: dict[str, QTextCharFormat] = {}
        self.defined: frozenset[str] | None = None  # None: no successful parse yet, no semantic layer
        self.unused: frozenset[str] = frozenset()
        self.set_theme(theme)

    def set_symbols(self, defined: frozenset[str] | None, unused: frozenset[str]) -> None:
        if (defined, unused) != (self.defined, self.unused):
            self.defined, self.unused = defined, unused
            self.rehighlight()

    def _semantic(self, role: str, word: str) -> str:
        name = word.lower()
        if self.defined is None:
            return role
        if role == "rule.ref" and name not in self.defined:
            return "rule.undefined"
        if role == "rule.def" and name in self.unused:
            return "rule.unused"
        return role

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self._formats.clear()
        self.rehighlight()

    def _format(self, role: str) -> QTextCharFormat:
        if role not in self._formats:
            self._formats[role] = syntax_format(self.theme, role)
        return self._formats[role]

    def highlightBlock(self, text: str) -> None:  # noqa: N802 - Qt override
        state = max(self.previousBlockState(), 0)
        tokens, end_state = lex_line(text, state)
        for start, length, role in tokens:
            self.setFormat(start, length, self._format(self._semantic(role, text[start : start + length])))
        self.setCurrentBlockState(end_state)
