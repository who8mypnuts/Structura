"""Fold ranges for the editor (docs/12 §2.1): brace blocks (rules, v2 material/light/camera/render blocks)
and runs of comment lines. Qt-free; computed from the same lexer as highlighting, so braces inside comments
never open a fold.

A range keeps its ``start`` line visible and hides ``start + 1 … end`` (0-based line numbers).
"""

from __future__ import annotations

from dataclasses import dataclass

from .highlight import IN_BLOCK_COMMENT, lex_line

MIN_COMMENT_RUN = 2  # a single comment line is not worth folding


@dataclass(frozen=True)
class FoldRange:
    start: int
    end: int
    kind: str  # "block" | "comment"


def _closing_line_has_code(line: str, brace_column: int) -> bool:
    """True when something other than a comment follows the closing brace (e.g. ``} R1``)."""
    rest = line[brace_column + 1 :].strip()
    return bool(rest) and not rest.startswith(("//", "/*"))


def _block_range(lines: list[str], start: int, end: int, brace_column: int) -> FoldRange | None:
    if _closing_line_has_code(lines[end], brace_column):
        end -= 1  # keep the closing line visible: it carries code
    return FoldRange(start, end, "block") if end > start else None


def _is_comment_line(line: str, tokens: list[tuple[int, int, str]]) -> bool:
    return bool(line.strip()) and bool(tokens) and all(role == "comment" for _, _, role in tokens)


def fold_ranges(text: str) -> tuple[FoldRange, ...]:
    """Every foldable range, ordered by start line (nested ranges included)."""
    lines = text.split("\n")
    ranges: list[FoldRange] = []
    stack: list[int] = []
    run_start: int | None = None
    state = 0
    for number, line in enumerate(lines):
        tokens, state_after = lex_line(line, state)
        for start, _, role in tokens:
            if role != "brace":
                continue
            if line[start] == "{":
                stack.append(number)
            elif stack:
                opened = stack.pop()
                if number > opened and (found := _block_range(lines, opened, number, start)) is not None:
                    ranges.append(found)
        inside_comment = state == IN_BLOCK_COMMENT and state_after == IN_BLOCK_COMMENT  # blank line in /* */
        comment = _is_comment_line(line, tokens) or (inside_comment and not line.strip())
        if comment and run_start is None:
            run_start = number
        elif not comment and run_start is not None:
            if number - run_start >= MIN_COMMENT_RUN:
                ranges.append(FoldRange(run_start, number - 1, "comment"))
            run_start = None
        state = state_after
    if run_start is not None and len(lines) - run_start >= MIN_COMMENT_RUN:
        ranges.append(FoldRange(run_start, len(lines) - 1, "comment"))
    return tuple(sorted(ranges, key=lambda r: (r.start, -r.end)))
