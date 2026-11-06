"""Text refactorings for the editor (docs/12 §2.2): rename a rule, find its references, format a script.
They work on the lexer's tokens, so comments and strings are never touched."""

from __future__ import annotations

from collections.abc import Iterator

from .highlight import lex_line

INDENT = "  "


def _lines(text: str) -> Iterator[tuple[int, str, list[tuple[int, int, str]]]]:
    """(offset of the line, line text, tokens) for every line, carrying block-comment state."""
    state, offset = 0, 0
    for line in text.split("\n"):
        tokens, state = lex_line(line, state)
        yield offset, line, tokens
        offset += len(line) + 1


def rule_occurrences(text: str, name: str) -> list[tuple[int, int]]:
    """(start, end) of every definition and reference of rule ``name`` (case-insensitive, tags excluded)."""
    target = name.lower()
    spans = []
    for offset, line, tokens in _lines(text):
        for start, length, role in tokens:
            word = line[start : start + length]
            if role in ("rule.def", "rule.ref") and word.lower() == target:
                spans.append((offset + start, offset + start + length))
    return spans


def rename_rule(text: str, old: str, new: str) -> str:
    if not new or any(c.isspace() or c in "{}[]" for c in new):
        raise ValueError(f"'{new}' is not a valid rule name")
    out = text
    for start, end in reversed(rule_occurrences(text, old)):
        out = out[:start] + new + out[end:]
    return out


def _depth_change(line: str, tokens: list[tuple[int, int, str]]) -> tuple[int, int]:
    """(closing braces that start the line, net depth change), counting real braces only."""
    leading, net, at_start = 0, 0, True
    for start, _, role in tokens:
        closing = role == "brace" and line[start] == "}"
        if role == "brace":
            net += -1 if closing else 1
        leading += 1 if at_start and closing else 0
        at_start = at_start and closing
    return leading, net


def format_script(text: str) -> str:
    """Re-indent by brace depth (two spaces), strip trailing whitespace. Idempotent; keeps comments."""
    out, depth, state = [], 0, 0
    for line in text.split("\n"):
        _, next_state = lex_line(line, state)
        body = line.strip()
        if state == 1 or not body:  # inside a block comment, or blank: keep as is (trimmed)
            out.append(line.rstrip())
        else:
            leading, net = _depth_change(line.strip(), lex_line(body, state)[0])
            out.append(INDENT * max(0, depth - leading) + body)
            depth = max(0, depth + net)
        state = next_state
    return "\n".join(out)
