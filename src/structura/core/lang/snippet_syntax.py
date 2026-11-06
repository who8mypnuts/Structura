"""Snippet tab stops (docs/12 §2.3), in the VS Code syntax: ``${1:default}``, ``$1`` and ``$0`` (the final
cursor). A stop index used more than once is mirrored: the later copies take the first one's text.
Qt-free; the editor runs the session (ui/editor/snippet_session.py)."""

from __future__ import annotations

import re
from dataclasses import dataclass

_STOP = re.compile(r"\$\{(\d+):([^}]*)\}|\$(\d+)")


@dataclass(frozen=True)
class Stop:
    index: int  # 1, 2, … ; 0 is the final cursor position
    start: int  # in the expanded text
    end: int


def expand(snippet: str) -> tuple[str, tuple[Stop, ...]]:
    """The text to insert (placeholders filled with their defaults, mirrors with the first default) and
    its stops in the order they are visited (1, 2, …, then 0)."""
    out: list[str] = []
    stops: list[Stop] = []
    defaults: dict[int, str] = {}
    position, last = 0, 0
    for match in _STOP.finditer(snippet):
        out.append(snippet[last : match.start()])
        position += match.start() - last
        index = int(match.group(1) or match.group(3))
        default = match.group(2) if match.group(1) else defaults.get(index, "")
        defaults.setdefault(index, default)
        stops.append(Stop(index, position, position + len(default)))
        out.append(default)
        position += len(default)
        last = match.end()
    out.append(snippet[last:])
    ordered = sorted(stops, key=lambda s: (s.index == 0, s.index, s.start))
    return "".join(out), tuple(ordered)


def has_stops(snippet: str) -> bool:
    return bool(_STOP.search(snippet))


def plain(snippet: str) -> str:
    """The snippet text without stop markup (menu titles, previews)."""
    return expand(snippet)[0]
