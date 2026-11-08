"""Edit named v2 blocks ('material NAME { … }', 'light NAME { … }') in script text (docs/05 §9).

New blocks go after the '#version 2' line and the blocks already there, so declarations stay together at the
top of the script. Block bodies never contain braces, so a block ends at its first '}'."""

from __future__ import annotations

import re

VERSION = re.compile(r"(?m)^[ \t]*#version[^\n]*\n?")
ANY_BLOCK = re.compile(r"(?ms)^[ \t]*(?:material|light|environment|camera|render)\b[^{\n]*\{[^}]*\}[ \t]*\n?")


def block_pattern(kind: str, name: str) -> re.Pattern[str]:
    return re.compile(rf"(?ms)^[ \t]*{kind}[ \t]+{re.escape(name)}[ \t]*\{{[^}}]*\}}[ \t]*\n?")


def block_span(text: str, kind: str, name: str) -> tuple[int, int] | None:
    match = block_pattern(kind, name).search(text)
    return (match.start(), match.end()) if match else None


def put_block(text: str, kind: str, name: str, block: str) -> str:
    """Replace the named block, or add it after the version line and the existing blocks."""
    block = block.rstrip("\n") + "\n"
    pattern = block_pattern(kind, name)
    if pattern.search(text):
        return pattern.sub(lambda _: block, text, count=1)
    anchor = max((m.end() for m in (*VERSION.finditer(text), *ANY_BLOCK.finditer(text))), default=0)
    return text[:anchor] + block + text[anchor:]


def remove_block(text: str, kind: str, name: str) -> str:
    return block_pattern(kind, name).sub("", text, count=1)


def block_names(text: str, kind: str) -> set[str]:
    """Names of the ``kind`` blocks written in ``text`` (before any build sees them)."""
    return set(re.findall(rf"(?m)^[ \t]*{kind}[ \t]+([A-Za-z_][\w-]*)[ \t]*\{{", text))
