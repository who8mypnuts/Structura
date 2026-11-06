"""Source documents, spans and line/column mapping."""

from __future__ import annotations

import bisect
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Span:
    """Half-open character range [start, end) in a text."""

    start: int
    end: int


@dataclass(frozen=True)
class LineIndex:
    """Maps character offsets to 1-based (line, column)."""

    starts: tuple[int, ...]

    @classmethod
    def of(cls, text: str) -> LineIndex:
        starts = [0]
        for i, ch in enumerate(text):
            if ch == "\n":
                starts.append(i + 1)
        return cls(tuple(starts))

    def position(self, offset: int) -> tuple[int, int]:
        line = bisect.bisect_right(self.starts, offset) - 1
        return line + 1, offset - self.starts[line] + 1


@dataclass(frozen=True)
class SourceDocument:
    """An immutable snapshot of a script."""

    text: str
    path: str = ""
    version: int = 0
    dialect: int = field(default=1)

    @classmethod
    def from_text(cls, text: str, path: str = "", version: int = 0) -> SourceDocument:
        return cls(text, path, version, detect_dialect(text))


def is_javascript(text: str) -> bool:
    """A Structure Synth '#javascript' script (docs/16 §3): the first line is '#javascript'."""
    return text.partition("\n")[0].strip().lower() == "#javascript"


def detect_dialect(text: str) -> int:
    """2 if the first non-blank line is '#version 2', else 1 (docs/05 §0)."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return 2 if stripped.lower().replace(" ", "") == "#version2" else 1
    return 1
