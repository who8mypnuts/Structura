"""Line-at-a-time lexical classification for editor highlighting (docs/12 §1).

``lex_line(text, state)`` returns (tokens, end_state); a token is (start, length, role) with roles named
like the theme's syntax roles without the 'syntax.' prefix. ``state`` is 1 inside a block comment. The
vocabulary comes from the language catalogues, so the editor holds no EisenScript knowledge of its own.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache

from ..color.names import NAMED_COLORS
from .catalog import all_primitives, modifiers, operator_names, set_commands
from .signatures import SIGNATURES

Token = tuple[int, int, str]
IN_BLOCK_COMMENT = 1
IN_V2_BLOCK = 2  # inside 'material … { … }' and friends: words are keys
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_.\-]*(::[A-Za-z0-9_]+)?")
_NUMBER = re.compile(r"[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?(/\d+)?")
_HEX = re.compile(r"#[0-9A-Fa-f]{3}(?:[0-9A-Fa-f]{3})?\b")
_PREPROCESSOR = re.compile(r"\s*#(define|include|version|param|javascript)\b")
COLOR_CONTEXT = {"color", "c", "blend", "background"}
BLOCKS = {"material", "light", "environment", "camera", "render"}  # v2 top-level blocks


@dataclass(frozen=True)
class Vocabulary:
    operators: frozenset[str]
    modifiers: frozenset[str]
    primitives: frozenset[str]
    set_keys: frozenset[str]


@cache
def vocabulary() -> Vocabulary:
    mods = {m.name for m in modifiers()} | {a.name for m in modifiers() for a in m.aliases}
    ops = set(operator_names()) - mods
    keys = {s.key for s in set_commands()} | {a for s in set_commands() for a in s.aliases}
    prims = {p.name for p in all_primitives()} | {"triangle"}  # triangle[…] is parsed separately by the resolver
    return Vocabulary(frozenset(ops), frozenset(mods), frozenset(prims), frozenset(keys))


class _LineLexer:
    def __init__(self, text: str) -> None:
        self.text, self.pos = text, 0
        self.tokens: list[Token] = []
        self.prev = ""  # previous word (lower-case) on this line, for context rules
        self.in_comment = False  # the line ends inside a block comment
        self.in_block = False  # inside a v2 block body
        self.block_header = False  # after 'material' etc., before its '{'

    def add(self, length: int, role: str) -> None:
        self.tokens.append((self.pos, length, role))
        self.pos += length

    def block_comment(self, skip: int = 0) -> None:
        """Consume a block comment starting at pos (``skip`` = length of an opening '/*')."""
        end = self.text.find("*/", self.pos + skip)
        self.in_comment = end < 0
        self.add((len(self.text) if end < 0 else end + 2) - self.pos, "comment")

    def word_role(self, word: str) -> str:
        lower = word.lower()
        if self.in_block:
            return "set.key" if not self.prev_is_value else "set.value"
        if self.block_header:
            return "tag"
        base = lower.split("::")[0]
        v = vocabulary()
        rules = (
            (self.prev == "rule", "rule.def"),
            ((self.prev == "set" and lower in v.set_keys) or lower.startswith("raytracer::"), "set.key"),
            (lower in ("rule", "set"), "keyword"),
            (lower in BLOCKS and not self.prev, "block"),
            (self.prev in COLOR_CONTEXT and (lower in NAMED_COLORS or lower == "random"), "color"),
            ("::" in lower and base in v.primitives, "tag"),
            (base in v.primitives, "primitive"),
            (lower in v.modifiers, "modifier"),
            (lower in v.operators, "operator"),
            (self.prev_is_set_key(), "set.value"),
        )
        return next((role for matched, role in rules if matched), "rule.ref")

    @property
    def prev_is_value(self) -> bool:
        return bool(self.tokens) and self.tokens[-1][2] == "set.key"

    def prev_is_set_key(self) -> bool:
        return any(role == "set.key" for _, _, role in self.tokens)

    def step(self) -> None:
        text, pos = self.text, self.pos
        ch = text[pos]
        if text.startswith("//", pos):
            self.add(len(text) - pos, "comment")
        elif text.startswith("/*", pos):
            self.block_comment(2)
        elif ch in "{}":
            self.in_block = ch == "{" and self.block_header
            self.block_header = self.block_header and ch != "{"
            self.add(1, "brace")
        elif ch == "[":
            end = text.find("]", pos)
            self.add((end + 1 if end >= 0 else len(text)) - pos, "bracket.arg")
        elif ch in "*>":
            self.add(1, "operator")
        elif m := _HEX.match(text, pos):
            self.add(m.end() - pos, "color")
        elif m := _NUMBER.match(text, pos):
            self.add(m.end() - pos, "set.value" if self.prev_is_set_key() else "number")
        elif m := _WORD.match(text, pos):
            word = m.group(0)
            called = word.lower() in SIGNATURES and text[m.end() :].lstrip().startswith("(")
            role = "function" if called else self.word_role(word)
            self.add(len(word), role)
            self.block_header = self.block_header or role == "block"
            self.prev = word.lower()
        else:
            self.pos += 1


def lex_line(text: str, state: int = 0) -> tuple[list[Token], int]:
    lexer = _LineLexer(text)
    lexer.in_block = state == IN_V2_BLOCK
    if state == IN_BLOCK_COMMENT:
        lexer.block_comment()
    elif _PREPROCESSOR.match(text):
        return [(0, len(text), "preprocessor")], 0
    elif text.lstrip().startswith("#") and not _HEX.match(text.lstrip()):
        return [(0, len(text), "comment")], 0
    while lexer.pos < len(text) and not lexer.in_comment:
        lexer.step()
    if lexer.in_comment:
        return lexer.tokens, IN_BLOCK_COMMENT
    return lexer.tokens, IN_V2_BLOCK if lexer.in_block else 0
