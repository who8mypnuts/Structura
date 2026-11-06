"""EisenScript v1 tokenizer (docs/05-eisenscript-language.md §1, docs/06 §4).

Scanning rules (Structure Synth 1.5 behaviour):
  * Separators are space, CR, LF, '{' and '}' (braces are also tokens). Tabs are *not* separators: all
    whitespace inside a token is deleted, so "x<TAB>1" becomes the single token "x1".
  * '#' at the start of a line starts a line comment; so does '//'. Only CR ends a line comment.
  * '/*' starts a block comment and '*/' ends one; both markers are recognised even inside a line comment,
    and '*/' is consumed anywhere.
  * '[' … ']' is read verbatim (spaces, newlines and all) and appended to the current token.
  * Tokens are classified as keyword, brace, '>' , '*', number (int, float or integer fraction a/b),
    operator (with abbreviations resolved) or user string (lower-cased).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from ..diagnostics import ParseError
from ..source import Span

LEGACY_OPERATORS = {
    "c": "color",
    "reflect": "reflect",
    "color": "color",
    "blend": "blend",
    "a": "alpha",
    "alpha": "alpha",
    "matrix": "matrix",
    "h": "hue",
    "hue": "hue",
    "sat": "sat",
    "b": "brightness",
    "brightness": "brightness",
    "v": "v",
    "x": "x",
    "y": "y",
    "z": "z",
    "rx": "rx",
    "ry": "ry",
    "rz": "rz",
    "s": "s",
    "fx": "fx",
    "fy": "fy",
    "fz": "fz",
    "maxdepth": "maxdepth",
    "weight": "weight",
    "md": "maxdepth",
    "w": "weight",
}
_INT = re.compile(r"[+-]?\d+")
_FLOAT = re.compile(r"[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?")
INT_MIN, INT_MAX = -(2**31), 2**31 - 1


class Kind(Enum):
    RULE = "rule"
    SET = "set"
    LBRACE = "{"
    RBRACE = "}"
    GT = ">"
    STAR = "*"
    NUMBER = "number"
    OPERATOR = "operator"
    USER = "user"
    END = "end"


@dataclass(frozen=True, slots=True)
class Token:
    kind: Kind
    text: str  # lower-cased user string / canonical operator name / raw number text
    span: Span
    value: float = 0.0
    is_integer: bool = False

    @property
    def number(self) -> float:
        return self.value


def _parse_int(text: str) -> int | None:
    if not _INT.fullmatch(text):
        return None
    value = int(text)
    return value if INT_MIN <= value <= INT_MAX else None


def _number_token(text: str, span: Span) -> Token:
    if text.count("/") == 1:
        num, den = (_parse_int(part) or 0 for part in text.split("/"))
        if num and den:
            return Token(Kind.NUMBER, text, span, num / den, False)
        raise ParseError(f"Invalid fraction found: {text}", span, "E004")
    as_int = _parse_int(text)
    if as_int is not None:
        return Token(Kind.NUMBER, text, span, float(as_int), True)
    if _FLOAT.fullmatch(text):
        return Token(Kind.NUMBER, text, span, float(text), False)
    raise ParseError(f"Invalid symbol found: {text}", span, "E004")


_SIMPLE = {"rule": Kind.RULE, "set": Kind.SET, "{": Kind.LBRACE, "}": Kind.RBRACE, ">": Kind.GT, "*": Kind.STAR}


def classify(text: str, span: Span) -> Token:
    lower = text.lower()
    if lower in _SIMPLE:
        return Token(_SIMPLE[lower], text, span)
    if text[0] in "+-0123456789":
        return _number_token(text, span)
    if lower in LEGACY_OPERATORS:
        return Token(Kind.OPERATOR, LEGACY_OPERATORS[lower], span)
    return Token(Kind.USER, lower, span)


class _Scanner:
    def __init__(self, text: str) -> None:
        self.src = text + " "
        self.pieces: list[tuple[str, Span]] = []
        self.current: list[str] = []
        self.start = 0
        self.in_line = False
        self.in_block = False

    def flush(self, end: int, strip: bool = True) -> None:
        raw = "".join(self.current)
        text = "".join(ch for ch in raw if not ch.isspace()) if strip else raw
        if text:
            self.pieces.append((text, Span(self.start, end)))
        self.current = []

    def add(self, i: int, ch: str) -> None:
        if not self.current:
            self.start = i
        self.current.append(ch)

    def comment_marker(self, i: int) -> int:
        """Handle comment syntax at i; returns the number of characters consumed (0 if none)."""
        src, ch = self.src, self.src[i]
        if ch == "#" and (i == 0 or src[i - 1] in "\r\n"):
            self.in_line = True
            return 2
        pair = src[i : i + 2] if i < len(src) - 1 else ""
        if pair == "*/":
            self.in_block = False
        elif pair == "//":
            self.in_line = True
        elif pair == "/*":
            self.in_block = True
        else:
            return 0
        return 2

    def bracket(self, i: int) -> int:
        src = self.src
        while i < len(src) and src[i] != "]":
            self.add(i, src[i])
            i += 1
        if i >= len(src):
            raise ParseError("No matching ']' found for '['", Span(self.start, i), "E002")
        self.add(i, "]")
        self.flush(i + 1, strip=False)
        return i + 1

    def run(self) -> list[tuple[str, Span]]:
        i, src = 0, self.src
        while i < len(src):
            ch = src[i]
            if ch == "\r":
                self.in_line = False
            consumed = self.comment_marker(i)
            if consumed:
                i += consumed
                continue
            if self.in_line or self.in_block:
                i += 1
            elif ch == "[":
                i = self.bracket(i)
            elif ch in "{} \r\n":
                self.flush(i)
                if ch in "{}":
                    self.pieces.append((ch, Span(i, i + 1)))
                i += 1
            else:
                self.add(i, ch)
                i += 1
        return self.pieces


def tokenize(text: str) -> list[Token]:
    """Tokenize preprocessed EisenScript (v1 rules). Raises ParseError like Structure Synth 1.5."""
    tokens = [classify(piece, span) for piece, span in _Scanner(text).run()]
    end = len(text)
    tokens.append(Token(Kind.END, "#END#", Span(end, end)))
    return tokens
