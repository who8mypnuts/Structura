"""Line-at-a-time highlighting for '#javascript' scripts (docs/16 §3), with the same token and state
conventions as core.lang.highlight.lex_line (state 1 = inside a block comment)."""

from __future__ import annotations

import re

from .highlight import IN_BLOCK_COMMENT, Token

KEYWORDS = frozenset(
    [
        "var",
        "let",
        "const",
        "function",
        "return",
        "if",
        "else",
        "for",
        "while",
        "do",
        "break",
        "continue",
        "new",
        "true",
        "false",
        "null",
        "undefined",
        "this",
        "typeof",
        "instanceof",
        "in",
        "of",
        "switch",
        "case",
        "default",
        "try",
        "catch",
        "finally",
        "throw",
    ]
)
_TOKEN = re.compile(
    r"(?P<comment>//.*)|(?P<block>/\*)|(?P<string>'(?:\\.|[^'\\])*'?|\"(?:\\.|[^\"\\])*\"?)"
    r"|(?P<number>\b\d+(?:\.\d*)?(?:[eE][+-]?\d+)?\b)|(?P<word>[A-Za-z_$][\w$]*)"
)


def _word_role(line: str, match: re.Match[str]) -> str | None:
    word = match.group(0)
    if word in KEYWORDS:
        return "keyword"
    if word == "Builder":
        return "primitive"
    if match.start() > 0 and line[match.start() - 1] == ".":
        return "function"
    return None


def lex_js_line(line: str, state: int = 0) -> tuple[list[Token], int]:
    tokens: list[Token] = []
    pos = 0
    if state == IN_BLOCK_COMMENT:
        end = line.find("*/")
        if end < 0:
            return [(0, len(line), "comment")], IN_BLOCK_COMMENT
        tokens.append((0, end + 2, "comment"))
        pos = end + 2
    if pos == 0 and line.strip().lower() == "#javascript":
        return [(0, len(line), "preprocessor")], 0
    while (match := _TOKEN.search(line, pos)) is not None:
        kind, pos = match.lastgroup, match.end()
        if kind == "block":
            end = line.find("*/", match.end())
            if end < 0:
                tokens.append((match.start(), len(line) - match.start(), "comment"))
                return tokens, IN_BLOCK_COMMENT
            tokens.append((match.start(), end + 2 - match.start(), "comment"))
            pos = end + 2
            continue
        role = _word_role(line, match) if kind == "word" else kind
        if role:
            tokens.append((match.start(), match.end() - match.start(), role))
    return tokens, 0
