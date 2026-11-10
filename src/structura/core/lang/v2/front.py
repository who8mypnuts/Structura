"""The v2 front passes, run before the v1 preprocessor (docs/05 §9)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ...scene.declarations import SceneDeclarations
from ..diagnostics import Diagnostic
from ..highlight import lex_line
from ..source import Span, detect_dialect
from .blocks import HEADER, extract_blocks
from .expressions import params_to_defines, substitute_expressions

_PARAM = re.compile(r"(?m)^[ \t]*#param\b.*$")
_VERSION = re.compile(r"(?m)^[ \t]*#[ \t]*version[ \t]*2[ \t]*$")


@dataclass(frozen=True)
class Front:
    text: str  # what the v1 preprocessor sees
    declarations: SceneDeclarations | None = None
    diagnostics: tuple[Diagnostic, ...] = field(default=())

    @property
    def v2(self) -> bool:
        return self.declarations is not None


def front(text: str) -> Front:
    """v1 scripts pass through unchanged; v2 scripts lose their blocks and gain #define sliders for #param."""
    if detect_dialect(text) != 2:
        return Front(text)
    extracted = extract_blocks(text)
    return Front(params_to_defines(extracted.text), extracted.declarations, tuple(extracted.diagnostics))


def timeline_names(frame: int = 0, fps: float = 24.0) -> dict[str, float]:
    """The animation variables of v2 expressions (docs/16 §2)."""
    return {"frame": float(frame), "time": frame / fps, "fps": float(fps)}


def after_preprocessing(source: str, fr: Front, names: dict[str, float] | None = None) -> str:
    """v2: evaluate '( expr )' once the defines and parameters have been substituted."""
    return substitute_expressions(source, names or timeline_names()) if fr.v2 else source


def _first_paren(text: str) -> tuple[int, int] | None:
    """The first '(' in code, skipping comments and preprocessor lines (v1 code never uses parentheses)."""
    if "(" not in text:
        return None  # the common case: no need to lex
    offset, state = 0, 0
    for line in text.split("\n"):
        tokens, state_after = lex_line(line, state)
        skipped = [(s, s + n) for s, n, role in tokens if role in ("comment", "preprocessor")]
        for column, char in enumerate(line):
            if char == "(" and not any(a <= column < b for a, b in skipped):
                return offset + column, offset + column + 1
        offset, state = offset + len(line) + 1, state_after
    return None


def misplaced_version(text: str) -> Span | None:
    """A '#version 2' line that does not select v2 because it is not the first non-blank line."""
    if detect_dialect(text) == 2:
        return None
    match = _VERSION.search(text)
    return Span(*match.span()) if match else None


def v2_syntax(text: str) -> Span | None:
    """The first v2-only construct in a script without '#version 2' (blocks, #param, '( expression )')."""
    if detect_dialect(text) == 2:
        return None
    found = [m.span() for m in (HEADER.search(text), _PARAM.search(text)) if m is not None]
    paren = _first_paren(text)
    found += [paren] if paren else []
    return Span(*min(found)) if found else None
