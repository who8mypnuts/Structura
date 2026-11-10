"""Edit named v2 blocks ('material NAME { … }', 'light NAME { … }') in script text (docs/05 §9).

New blocks go after the '#version 2' line and the blocks already there, so declarations stay together at the
top of the script. Block bodies never contain braces, so a block ends at its first '}'."""

from __future__ import annotations

import re

VERSION = re.compile(r"(?m)^[ \t]*#version[^\n]*\n?")
ANY_BLOCK = re.compile(r"(?ms)^[ \t]*(?:material|light|environment|camera|render)\b[^{\n]*\{[^}]*\}[ \t]*\n?")


def block_pattern(kind: str, name: str) -> re.Pattern[str]:
    """Returns the pattern of one block, with its line ending.

    Args:
        kind: The block kind ('material', 'light', 'environment' …).
        name: The block's name; "" matches the unnamed block of that kind ('environment { … }').
    """
    gap = r"[ \t]+" if name else r"[ \t]*"
    return re.compile(rf"(?ms)^[ \t]*{kind}{gap}{re.escape(name)}[ \t]*\{{[^}}]*\}}[ \t]*\n?")


def block_span(text: str, kind: str, name: str) -> tuple[int, int] | None:
    match = block_pattern(kind, name).search(text)
    return (match.start(), match.end()) if match else None


def put_block(text: str, kind: str, name: str, block: str) -> str:
    """Replaces a block, or adds it after the version line and the existing blocks.

    Args:
        text: The script.
        kind: The block kind.
        name: The block's name ("" for an unnamed block).
        block: The new block text.

    Returns:
        The new script text.
    """
    block = block.rstrip("\n") + "\n"
    pattern = block_pattern(kind, name)
    if pattern.search(text):
        return pattern.sub(lambda _: block, text, count=1)
    return append_block(text, block)


def append_block(text: str, block: str) -> str:
    """Adds text after the version line and the existing blocks, so declarations stay together at the top.

    Args:
        text: The script.
        block: One or more blocks (comments allowed).

    Returns:
        The new script text.
    """
    block = block.rstrip("\n") + "\n"
    anchor = max((m.end() for m in (*VERSION.finditer(text), *ANY_BLOCK.finditer(text))), default=0)
    return text[:anchor] + block + text[anchor:]


def remove_block(text: str, kind: str, name: str) -> str:
    return block_pattern(kind, name).sub("", text, count=1)


def block_names(text: str, kind: str) -> set[str]:
    """Names of the ``kind`` blocks written in ``text`` (before any build sees them)."""
    return set(re.findall(rf"(?m)^[ \t]*{kind}[ \t]+([A-Za-z_][\w-]*)[ \t]*\{{", text))
