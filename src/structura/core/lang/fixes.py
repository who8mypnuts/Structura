"""Quick fixes for diagnostics (docs/12 §2.2, Ctrl+.). Qt-free: a fix is a titled list of text edits in
original positions. Which fix a code offers is declared in catalog/diagnostics.toml ('fix = …')."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from .catalog import diagnostic_specs, operator_names
from .diagnostics import Diagnostic
from .highlight import lex_line

DEFAULT_MAXDEPTH = 100
_NAME = re.compile(r"[A-Za-z_][\w]*(?:::[\w]+)?")


@dataclass(frozen=True)
class TextEdit:
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class QuickFix:
    title: str
    edits: tuple[TextEdit, ...]


def apply_edits(text: str, edits: tuple[TextEdit, ...]) -> str:
    for edit in sorted(edits, key=lambda e: e.start, reverse=True):
        text = text[: edit.start] + edit.text + text[edit.end :]
    return text


def _line_bounds(text: str, position: int) -> tuple[int, int]:
    """The line containing ``position``, including its newline."""
    start = text.rfind("\n", 0, position) + 1
    end = text.find("\n", position)
    return start, len(text) if end < 0 else end + 1


def _matching_brace(text: str, opening: int) -> int | None:
    """The '}' closing the '{' at ``opening`` (braces in comments ignored)."""
    depth, offset, state = 0, 0, 0
    for line in text.split("\n"):
        tokens, state_after = lex_line(line, state)
        for start, _, role in tokens:
            at = offset + start
            if role != "brace" or at < opening:
                continue
            depth += 1 if line[start] == "{" else -1
            if depth == 0:
                return at
        offset, state = offset + len(line) + 1, state_after
    return None


def _first_code_line(text: str) -> int:
    """Offset of the first line that is not blank, a comment or a preprocessor line (insertion point)."""
    offset = 0
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped and not stripped.startswith(("//", "#", "/*", "*")):
            return offset
        offset += len(line) + 1
    return len(text)


def _create_rule(text: str, d: Diagnostic) -> QuickFix | None:
    assert d.span is not None
    words = _NAME.findall(text[d.span.start : d.span.end])  # the span may cover '{ x 1 } missing'
    name = words[-1].split("::")[0] if words else ""
    if not name.isidentifier():
        return None
    tail = "" if text.endswith("\n") else "\n"
    return QuickFix(f"Create rule '{name}'", (TextEdit(len(text), len(text), f"{tail}\nrule {name} {{\n  box\n}}\n"),))


def _remove_rule(text: str, d: Diagnostic) -> QuickFix | None:
    assert d.span is not None
    opening = text.find("{", d.span.start)
    closing = _matching_brace(text, opening) if opening >= 0 else None
    if closing is None:
        return None
    start, _ = _line_bounds(text, d.span.start)
    _, end = _line_bounds(text, closing)
    header = text[d.span.start : d.span.end].split()
    name = header[1] if len(header) > 1 else ""
    return QuickFix(f"Remove unused rule '{name}'", (TextEdit(start, end, ""),))


def _canonical_alias(text: str, d: Diagnostic) -> QuickFix | None:
    assert d.span is not None
    spelled = text[d.span.start : d.span.end]
    canonical = operator_names().get(spelled, (spelled, True))[0]
    return QuickFix(f"Replace '{spelled}' with '{canonical}'", (TextEdit(d.span.start, d.span.end, canonical),))


def _add_maxdepth(text: str, d: Diagnostic) -> QuickFix | None:
    at = _first_code_line(text)
    return QuickFix(f"Add 'set maxdepth {DEFAULT_MAXDEPTH}'", (TextEdit(at, at, f"set maxdepth {DEFAULT_MAXDEPTH}\n"),))


def _remove_line(text: str, d: Diagnostic) -> QuickFix | None:
    assert d.span is not None
    start, end = _line_bounds(text, d.span.start)
    return QuickFix(f"Remove '{text[d.span.start : d.span.end]}'", (TextEdit(start, end, ""),))


def _add_version(text: str, d: Diagnostic) -> QuickFix | None:
    return QuickFix("Add '#version 2' (EisenScript v2)", (TextEdit(0, 0, "#version 2\n"),))


def _rename_key(text: str, d: Diagnostic) -> QuickFix | None:
    """W115: replace a misspelt block key with the suggestion its message makes."""
    assert d.span is not None
    match = re.search(r"did you mean '([\w-]+)'", d.message)
    if match is None:
        return None
    return QuickFix(f"Change to '{match.group(1)}'", (TextEdit(d.span.start, d.span.end, match.group(1)),))


def _move_version(text: str, d: Diagnostic) -> QuickFix | None:
    assert d.span is not None
    start, end = _line_bounds(text, d.span.start)
    return QuickFix("Move '#version 2' to the first line", (TextEdit(0, 0, "#version 2\n"), TextEdit(start, end, "")))


FIXERS: dict[str, Callable[[str, Diagnostic], QuickFix | None]] = {
    "create_rule": _create_rule,
    "remove_rule": _remove_rule,
    "canonical_alias": _canonical_alias,
    "add_maxdepth": _add_maxdepth,
    "remove_line": _remove_line,
    "add_version": _add_version,
    "move_version": _move_version,
    "rename_key": _rename_key,
}


def quick_fixes(text: str, diagnostics: list[Diagnostic] | tuple[Diagnostic, ...]) -> list[QuickFix]:
    """The fixes offered for ``diagnostics`` (typically those at the cursor), without duplicates."""
    fixes: list[QuickFix] = []
    for d in diagnostics:
        spec = diagnostic_specs().get(d.code)
        fixer = FIXERS.get(spec.fix) if spec else None
        fix = fixer(text, d) if fixer and d.span is not None else None
        if fix is not None and fix not in fixes:
            fixes.append(fix)
    return fixes
