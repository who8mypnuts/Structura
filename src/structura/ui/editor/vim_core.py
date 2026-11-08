"""Vim keybindings, the pure part (docs/12 §2.1, P2): parsing normal-mode key sequences and the motions, on
plain text and character offsets. ui/editor/vim.py applies them to the editor."""

from __future__ import annotations

import re
from dataclasses import dataclass

MOTIONS = "hjklwbeWBE0^$G{}%;,"
INCLUSIVE = set("e$%EfFtT")  # an operator includes the character the motion lands on
LINEWISE = set("jkG") | {"gg"}
OPERATORS = "dcy<>"
SIMPLE = "xXsSpPuJ~iaIAoOvVDCYnN.:/"
COMMAND = re.compile(
    rf"^(?P<count>[1-9]\d*)?(?:(?P<op>[{OPERATORS}])(?P<count2>[1-9]\d*)?)?"
    rf"(?P<motion>gg|[fFtT].|[{re.escape(MOTIONS)}]|[{OPERATORS}])$"
)
SINGLE = re.compile(rf"^(?P<count>[1-9]\d*)?(?P<cmd>r.|[{re.escape(SIMPLE)}])$")
PARTIAL = re.compile(rf"^([1-9]\d*)?([{OPERATORS}]([1-9]\d*)?)?(g|[fFtTr])?$")


@dataclass(frozen=True)
class Command:
    count: int  # 1 when not given; operator and motion counts multiply (2d3w = 6 words)
    operator: str  # '' for a plain motion or command
    motion: str  # a motion ('w', 'fx', 'gg'), the operator again for 'dd', or a simple command ('x', 'rq')
    explicit: bool = False  # a count was typed (G: go to that line)


def parse(keys: str) -> Command | bool | None:
    """A complete Command, True while more keys are needed, or None for a sequence that means nothing."""
    if keys == "0":
        return Command(1, "", "0")
    m = COMMAND.match(keys)
    if m and (m["motion"] not in OPERATORS or m["motion"] == m["op"]):  # 'dd', never 'd' alone or 'dy'
        count = int(m["count"] or 1) * int(m["count2"] or 1)
        return Command(count, m["op"] or "", m["motion"], bool(m["count"] or m["count2"]))
    m = SINGLE.match(keys)
    if m:
        return Command(int(m["count"] or 1), "", m["cmd"], bool(m["count"]))
    return True if PARTIAL.match(keys) else None


# -- text helpers ----------------------------------------------------------------------------------------------
def line_start(text: str, pos: int) -> int:
    return text.rfind("\n", 0, pos) + 1


def line_end(text: str, pos: int) -> int:
    end = text.find("\n", pos)
    return len(text) if end < 0 else end


def column(text: str, pos: int) -> int:
    return pos - line_start(text, pos)


def _kind(ch: str, big: bool) -> int:
    if ch.isspace():
        return 0
    if big or ch.isalnum() or ch == "_":
        return 1
    return 2


def word_forward(text: str, pos: int, big: bool = False) -> int:
    n = len(text)
    if pos >= n:
        return n
    kind = _kind(text[pos], big)
    while pos < n and kind and _kind(text[pos], big) == kind:
        pos += 1
    while pos < n and text[pos].isspace():
        pos += 1
    return pos


def word_end(text: str, pos: int, big: bool = False) -> int:
    n = len(text)
    pos += 1
    while pos < n and text[pos].isspace():
        pos += 1
    if pos >= n:
        return max(0, n - 1)
    kind = _kind(text[pos], big)
    while pos + 1 < n and _kind(text[pos + 1], big) == kind:
        pos += 1
    return pos


def word_back(text: str, pos: int, big: bool = False) -> int:
    pos -= 1
    while pos > 0 and text[pos].isspace():
        pos -= 1
    if pos <= 0:
        return 0
    kind = _kind(text[pos], big)
    while pos > 0 and _kind(text[pos - 1], big) == kind:
        pos -= 1
    return pos


def vertical(text: str, pos: int, lines: int, goal: int) -> int:
    """``lines`` down (negative: up), at column ``goal`` or the line's last character."""
    start = line_start(text, pos)
    for _ in range(abs(lines)):
        if lines > 0:
            end = line_end(text, start)
            if end >= len(text):
                break
            start = end + 1
        else:
            if start == 0:
                break
            start = line_start(text, start - 1)
    end = line_end(text, start)
    return min(start + goal, max(start, end - 1))


def line_number_pos(text: str, line: int) -> int:
    """Offset of the first non-blank of 1-based ``line`` (clamped)."""
    starts = [0] + [m.end() for m in re.finditer("\n", text)]
    start = starts[max(0, min(line, len(starts)) - 1)]
    return first_non_blank(text, start)


def first_non_blank(text: str, pos: int) -> int:
    start, end = line_start(text, pos), line_end(text, pos)
    body = text[start:end]
    return start + (len(body) - len(body.lstrip(" \t")))


def paragraph(text: str, pos: int, forward: bool) -> int:
    """The next (previous) blank line, or the end (start) of the text."""
    lines = text.split("\n")
    starts = [0]
    for line in lines[:-1]:
        starts.append(starts[-1] + len(line) + 1)
    row = text.count("\n", 0, pos)
    step = 1 if forward else -1
    row += step
    while 0 <= row < len(lines) and lines[row].strip():
        row += step
    if row >= len(lines):
        return len(text)
    return 0 if row < 0 else starts[row]


def matching_bracket(text: str, pos: int) -> int:
    pairs = {"{": "}", "[": "]", "(": ")"}
    closers = {v: k for k, v in pairs.items()}
    start = pos
    while start < line_end(text, pos) and text[start] not in "{}[]()":
        start += 1
    if start >= len(text) or text[start] not in "{}[]()":
        return pos
    ch = text[start]
    forward = ch in pairs
    mate = pairs.get(ch) or closers[ch]
    depth, i = 0, start
    while 0 <= i < len(text):
        if text[i] == ch:
            depth += 1
        elif text[i] == mate:
            depth -= 1
            if depth == 0:
                return i
        i += 1 if forward else -1
    return pos


def find_char(text: str, pos: int, how: str, ch: str) -> int:
    """f/F/t/T within the line; the position unchanged when the character is not there."""
    start, end = line_start(text, pos), line_end(text, pos)
    if how in "ft":
        found = text.find(ch, pos + (2 if how == "t" else 1), end)
        return pos if found < 0 else found - (1 if how == "t" else 0)
    found = text.rfind(ch, start, pos - (1 if how == "T" else 0))
    return pos if found < 0 else found + (1 if how == "T" else 0)


def move(text: str, pos: int, motion: str, goal: int, last_find: str = "") -> int:
    """One step of ``motion`` from ``pos`` (counts are applied by the caller)."""
    simple = {
        "h": lambda: max(line_start(text, pos), pos - 1),
        "l": lambda: min(max(line_start(text, pos), line_end(text, pos) - 1), pos + 1),
        "j": lambda: vertical(text, pos, 1, goal),
        "k": lambda: vertical(text, pos, -1, goal),
        "w": lambda: word_forward(text, pos),
        "W": lambda: word_forward(text, pos, True),
        "b": lambda: word_back(text, pos),
        "B": lambda: word_back(text, pos, True),
        "e": lambda: word_end(text, pos),
        "E": lambda: word_end(text, pos, True),
        "0": lambda: line_start(text, pos),
        "^": lambda: first_non_blank(text, pos),
        "$": lambda: max(line_start(text, pos), line_end(text, pos) - 1),
        "{": lambda: paragraph(text, pos, False),
        "}": lambda: paragraph(text, pos, True),
        "%": lambda: matching_bracket(text, pos),
    }
    if motion in simple:
        return int(simple[motion]())
    if motion[0] in "fFtT" and len(motion) == 2:
        return find_char(text, pos, motion[0], motion[1])
    if motion in ";," and last_find:
        how = last_find[0] if motion == ";" else last_find[0].swapcase()
        return find_char(text, pos, how, last_find[1])
    return pos


def operator_range(text: str, pos: int, target: int, motion: str) -> tuple[int, int, bool]:
    """(start, end, linewise) of an operator from ``pos`` to the motion's ``target``."""
    if motion in LINEWISE or motion in OPERATORS:
        a, b = sorted((pos, target))
        start, end = line_start(text, a), line_end(text, b)
        return start, min(len(text), end + 1), True
    if motion in ("w", "W") and "\n" in text[pos:target]:
        target = line_end(text, pos)  # 'dw' on a line's last word stops at the line end
    a, b = sorted((pos, target))
    inclusive = motion[0] in INCLUSIVE
    return a, min(len(text), b + (1 if inclusive else 0)), False
