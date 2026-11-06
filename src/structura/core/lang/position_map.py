"""Map spans in the preprocessed text back to the text the user edits (docs/12 §5).

The v1 preprocessor keeps every line (joined with CR LF), so lines correspond 1:1. Columns are exact on
lines without substitutions and clamped to the line length on lines where a #define changed the text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .source import Span

_LINES = re.compile(r"\r\n|\r|\n")


def _starts(text: str) -> list[int]:
    return [0] + [m.end() for m in _LINES.finditer(text)]


@dataclass(frozen=True)
class PositionMap:
    original: str
    preprocessed: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "_orig_starts", _starts(self.original))
        object.__setattr__(self, "_pre_starts", _starts(self.preprocessed))

    def _line_of(self, starts: list[int], offset: int) -> int:
        lo, hi = 0, len(starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if starts[mid] <= offset:
                lo = mid
            else:
                hi = mid - 1
        return lo

    def _line_end(self, starts: list[int], text: str, line: int) -> int:
        end = starts[line + 1] if line + 1 < len(starts) else len(text)
        while end > starts[line] and text[end - 1] in "\r\n":
            end -= 1
        return end

    def offset(self, pre_offset: int) -> int:
        pre: list[int] = self._pre_starts  # type: ignore[attr-defined]
        orig: list[int] = self._orig_starts  # type: ignore[attr-defined]
        line = min(self._line_of(pre, pre_offset), len(orig) - 1)
        column = pre_offset - pre[line]
        return min(orig[line] + column, self._line_end(orig, self.original, line))

    def span(self, span: Span | None) -> Span | None:
        if span is None:
            return None
        start = self.offset(span.start)
        return Span(start, max(start, self.offset(span.end)))
