"""'#include "file.es"' (docs/05 §2.4, defect D4): the file's lines are inserted at that point, before any
other preprocessing. Paths resolve against the including file's folder, then the library folders
(Preferences ▸ Paths). Each file is included once; a file that includes itself (directly or not) and a file
that is not found are E012 errors on the #include line.

The analysis runs on the expanded text; ``Expansion.span`` maps its spans back to the edited file: the file's
own lines exactly, anything from an included file to the #include line that brought it in.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from .position_map import PositionMap
from .source import Span

INCLUDE = re.compile(r'^[ \t]*#include[ \t]+"([^"]+)"[ \t]*$')
_library: list[Path] = []


def set_library_paths(paths: Sequence[Path]) -> None:
    """The folders searched after the including file's own (Preferences ▸ Paths ▸ Library folders)."""
    _library[:] = [Path(p) for p in paths]


@dataclass(frozen=True)
class Expansion:
    text: str  # the script with the included files' lines inserted
    origins: tuple[int, ...] = ()  # per expanded line: the line of the edited file it comes from
    own: tuple[bool, ...] = ()  # per expanded line: the edited file's own line (not an included one)
    files: tuple[Path, ...] = ()
    problems: tuple[tuple[int, str], ...] = ()  # (line of the edited file, message)
    main_starts: tuple[int, ...] = field(default=())  # line starts of the edited file

    @property
    def active(self) -> bool:
        return bool(self.files or self.problems)

    def line_span(self, line: int, main: str) -> Span:
        start = self.main_starts[line]
        end = main.find("\n", start)
        return Span(start, len(main) if end < 0 else end)

    def offset(self, offset: int, main: str) -> tuple[int, bool]:
        """(offset in the edited file, whether it is exact) for an offset of the expanded text."""
        line = self.text.count("\n", 0, offset)
        if line >= len(self.origins):
            return len(main), False
        column = offset - (self.text.rfind("\n", 0, offset) + 1)
        origin = self.origins[line]
        if self.own[line]:
            return min(self.main_starts[origin] + column, len(main)), True
        return self.main_starts[origin], False

    def span(self, span: Span | None, main: str) -> Span | None:
        if span is None:
            return None
        (start, exact_a), (end, exact_b) = self.offset(span.start, main), self.offset(span.end, main)
        if exact_a and exact_b:
            return Span(start, max(start, end))
        line = self.origins[min(self.text.count("\n", 0, span.start), len(self.origins) - 1)]
        return self.line_span(line, main)


def _resolve(name: str, folder: Path | None) -> Path | None:
    for base in ([folder] if folder is not None else []) + _library:
        candidate = (base / name).resolve()
        if candidate.is_file():
            return candidate
    absolute = Path(name)
    return absolute if absolute.is_absolute() and absolute.is_file() else None


class _Expander:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.origins: list[int] = []
        self.own: list[bool] = []
        self.files: list[Path] = []
        self.problems: list[tuple[int, str]] = []

    def add(self, text: str, folder: Path | None, stack: tuple[Path, ...], origin: int | None) -> None:
        for index, line in enumerate(text.split("\n")):
            here = index if origin is None else origin
            match = INCLUDE.match(line)
            self.lines.append(" " * len(line) if match else line)
            self.origins.append(here)
            self.own.append(origin is None)
            if match:
                self._include(match.group(1), folder, stack, here)

    def _include(self, name: str, folder: Path | None, stack: tuple[Path, ...], origin: int) -> None:
        path = _resolve(name, folder)
        if path is None:
            self.problems.append((origin, f"Include file not found: {name}"))
        elif path in stack:
            self.problems.append((origin, f"'{name}' includes itself"))
        elif path not in self.files:  # each file once
            self.files.append(path)
            text = path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
            self.add(text, path.parent, (*stack, path), origin)


def expand_includes(text: str, folder: Path | None = None) -> Expansion:
    """``text`` with its #include lines expanded (unchanged, and inactive, when it has none)."""
    if "#include" not in text:
        return Expansion(text)
    expander = _Expander()
    expander.add(text, folder, (), None)
    starts = (0, *(m.end() for m in re.finditer("\n", text)))
    return Expansion("\n".join(expander.lines), tuple(expander.origins), tuple(expander.own),
                     tuple(expander.files), tuple(expander.problems), starts)  # fmt: skip


@dataclass(frozen=True)
class IncludeMap(PositionMap):
    """A PositionMap over the expanded text whose spans land in the edited file (Analysis.positions)."""

    expansion: Expansion = Expansion("")
    main: str = ""

    def span(self, span: Span | None) -> Span | None:
        return self.expansion.span(super().span(span), self.main)
