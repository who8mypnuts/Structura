"""Lexical highlighting through core.lang.highlight.lex_line (one lexer, no regexes here; docs/12 §1)."""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QTextDocument

from ...core.lang.analysis import Analysis
from ...core.lang.highlight import lex_line
from ...core.lang.js_highlight import lex_js_line
from ...themes.model import Theme
from ..theming import qcolor, syntax_format

LEX_BITS = 2  # block state = lexer state (2 bits) | brace depth << LEX_BITS
RAINBOW = 6  # editor.rainbow.1 … editor.rainbow.6


def lexer_state(block_state: int) -> int:
    """The lexer part of a block's user state (−1, 'not highlighted yet', reads as 0)."""
    return max(block_state, 0) & ((1 << LEX_BITS) - 1)


def brace_depth(block_state: int) -> int:
    return max(block_state, 0) >> LEX_BITS


class EisenHighlighter(QSyntaxHighlighter):
    """Lexical colours per block, refined by the latest analysis (defined / undefined / unused rules)."""

    def __init__(self, document: QTextDocument, theme: Theme) -> None:
        super().__init__(document)
        self._formats: dict[str, QTextCharFormat] = {}
        self.defined: frozenset[str] | None = None  # None: no successful parse yet, no semantic layer
        self.unused: frozenset[str] = frozenset()
        self.defines: frozenset[str] = frozenset()
        self.rainbow = False
        self.javascript = False  # a '#javascript' script: highlighted as JavaScript
        self.set_theme(theme)

    def set_rainbow(self, enabled: bool) -> None:
        if enabled != self.rainbow:
            self.rainbow = enabled
            self.rehighlight()

    def set_analysis(self, analysis: Analysis) -> None:
        """The semantic layer: defined / unused / undefined rules and '#define' names."""
        self.set_symbols(*analysis.semantic_symbols())

    def set_symbols(
        self, defined: frozenset[str] | None, unused: frozenset[str], defines: frozenset[str] = frozenset()
    ) -> None:
        if (defined, unused, defines) != (self.defined, self.unused, self.defines):
            self.defined, self.unused, self.defines = defined, unused, defines
            self.rehighlight()

    def _semantic(self, role: str, word: str) -> str:
        name = word.lower()
        if role == "rule.ref" and word in self.defines:
            return "define.substituted"
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

    def _rainbow_format(self, depth: int) -> QTextCharFormat:
        key = f"rainbow.{depth % RAINBOW + 1}"
        if key not in self._formats:
            fmt = QTextCharFormat(self._format("brace"))
            fmt.setForeground(qcolor(self.theme[f"editor.{key}"]))
            self._formats[key] = fmt
        return self._formats[key]

    def _check_language(self, text: str) -> None:
        """The first line decides the language; a change re-highlights the whole document (deferred)."""
        javascript = text.strip().lower() == "#javascript"
        if javascript != self.javascript:
            self.javascript = javascript
            QTimer.singleShot(0, self.rehighlight)

    def highlightBlock(self, text: str) -> None:  # noqa: N802 - Qt override
        if self.currentBlock().blockNumber() == 0:
            self._check_language(text)
        previous = self.previousBlockState()
        depth = brace_depth(previous)
        lexer = lex_js_line if self.javascript else lex_line
        tokens, end_state = lexer(text, lexer_state(previous))
        for start, length, role in tokens:
            if role == "brace":
                depth -= text[start] == "}"
                fmt = self._rainbow_format(max(depth, 0)) if self.rainbow else self._format(role)
                self.setFormat(start, length, fmt)
                depth += text[start] == "{"
                continue
            self.setFormat(start, length, self._format(self._semantic(role, text[start : start + length])))
        self.setCurrentBlockState(end_state | (max(depth, 0) << LEX_BITS))
