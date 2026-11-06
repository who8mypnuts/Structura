"""Bracket matching over the plain text (docs/12 §2.1)."""

from __future__ import annotations

OPEN, CLOSE = "{[(", "}])"
SCAN_LIMIT = 200_000


def match_bracket(text: str, pos: int) -> tuple[int, int] | None:
    """(bracket position, its partner) for a bracket just before or at ``pos``, if both exist."""
    for at in (pos - 1, pos):
        if 0 <= at < len(text) and text[at] in OPEN + CLOSE:
            partner = _partner(text, at)
            if partner is not None:
                return at, partner
    return None


def _partner(text: str, at: int) -> int | None:
    ch = text[at]
    forward = ch in OPEN
    mate = CLOSE[OPEN.index(ch)] if forward else OPEN[CLOSE.index(ch)]
    depth, step = 0, 1 if forward else -1
    i = at
    end = min(len(text), at + SCAN_LIMIT) if forward else max(-1, at - SCAN_LIMIT)
    while i != end:
        c = text[i]
        if c == ch:
            depth += 1
        elif c == mate:
            depth -= 1
            if depth == 0:
                return i
        i += step
    return None
