"""Find in Files (docs/12 §2.1), Qt-free: plain, whole-word or regular-expression search over named texts,
and the script files near a given file."""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

MAX_MATCHES = 2000
MAX_FILES = 500


@dataclass(frozen=True)
class Match:
    source: str  # the file or document the text came from
    line: int  # 0-based
    column: int
    length: int
    text: str  # the whole line
    offset: int  # position in the text


def pattern(query: str, regex: bool = False, case: bool = False, whole_word: bool = False) -> re.Pattern[str]:
    """Compile the search; an invalid regular expression raises re.error."""
    body = query if regex else re.escape(query)
    if whole_word:
        body = rf"\b(?:{body})\b"
    return re.compile(body, 0 if case else re.IGNORECASE)


def _line_matches(source: str, number: int, line: str, offset: int, compiled: re.Pattern[str]) -> Iterator[Match]:
    for m in compiled.finditer(line):
        if m.end() > m.start():  # an empty match (e.g. 'x*') finds nothing useful
            yield Match(source, number, m.start(), m.end() - m.start(), line, offset + m.start())


def search(texts: Mapping[str, str], compiled: re.Pattern[str], limit: int = MAX_MATCHES) -> list[Match]:
    found: list[Match] = []
    for source, text in texts.items():
        offset = 0
        for number, line in enumerate(text.split("\n")):
            found += _line_matches(source, number, line, offset, compiled)
            if len(found) >= limit:
                return found[:limit]
            offset += len(line) + 1
    return found


def script_files(folder: Path, limit: int = MAX_FILES) -> Iterator[Path]:
    """.es files under ``folder`` (sorted, at most ``limit``)."""
    for count, path in enumerate(sorted(folder.rglob("*.es"))):
        if count >= limit:
            return
        yield path
