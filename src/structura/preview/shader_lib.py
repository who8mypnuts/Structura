"""GLSL sources of the preview engine with a tiny '#include "file"' preprocessor (docs/08 §2)."""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path

SHADERS = Path(__file__).resolve().parent / "shaders"
INCLUDE = re.compile(r'^\s*#include\s+"([^"]+)"\s*$', re.MULTILINE)


@cache
def source(name: str) -> str:
    """The shader text with includes expanded (each file at most once)."""
    seen: set[str] = set()

    def expand(file: str) -> str:
        if file in seen:
            return ""
        seen.add(file)
        text = (SHADERS / file).read_text(encoding="utf-8")
        return INCLUDE.sub(lambda m: expand(m.group(1)), text)

    return expand(name)


def with_defines(text: str, defines: tuple[str, ...]) -> str:
    """Insert '#define NAME' lines right after the '#version' line."""
    if not defines:
        return text
    first, _, rest = text.partition("\n")
    return "\n".join([first, *(f"#define {d}" for d in defines), rest])


def program_sources(vertex: str, fragment: str, defines: tuple[str, ...] = ()) -> dict[str, str]:
    return {
        "vertex_shader": with_defines(source(vertex), defines),
        "fragment_shader": with_defines(source(fragment), defines),
    }
