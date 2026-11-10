"""Migrate a Structure Synth 1.5 (v1) script to EisenScript v2 (docs/16 §5 'structura convert --to v2').

v2 changes two things that can alter a v1 script's meaning, and the converter keeps the v1 result:

- ``#define`` and GUI parameters replace whole words in v2, substrings in v1. Lines where the two differ get
  the v1 substitution written out (a note lists them; those lines lose their slider link).
- v2 adds primitives (cone, torus, ellipsoid, tube) and the 'mat' operator. v1 rules with those names are
  renamed, with every reference.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .catalog import v2_primitives
from .legacy.gui_params import default_value, value_text
from .legacy.preprocessor import LegacyPreprocessor, substitute
from .source import detect_dialect

HEADER = "#version 2"
RESERVED_V2 = {p.name for p in v2_primitives()} - {"cylinder"} | {"mat"}


@dataclass(frozen=True)
class Conversion:
    text: str
    notes: tuple[str, ...]

    @property
    def changed(self) -> bool:
        return bool(self.notes)


def _word(name: str) -> re.Pattern[str]:
    """``name`` as a rule reference (rule names are case-insensitive; not inside 'box::name' or 'name[…]')."""
    return re.compile(rf"(?<![A-Za-z0-9_:]){re.escape(name)}(?![A-Za-z0-9_\[])", re.IGNORECASE)


def _defines(text: str) -> dict[str, str]:
    """Every #define and GUI parameter with its v1 value (parameters at their defaults)."""
    pre = LegacyPreprocessor().process(text)
    table = dict(pre.defines)
    table |= {p.name: value_text(p, default_value(p)) for p in pre.parameters}
    return table


def _bake_substrings(lines: list[str], table: dict[str, str], notes: list[str]) -> None:
    for i, line in enumerate(lines):
        if line.startswith("#") or not table:
            continue
        v1, _ = substitute(line, table)
        v2, _ = substitute(line, table, whole_words=True)
        if v1 != v2:
            lines[i] = v1
            notes.append(f"line {i + 1}: #define substitution inside words written out (v2 replaces whole words)")


def _rule_names(text: str) -> set[str]:
    return {m.group(1).lower() for m in re.finditer(r"(?im)^\s*rule\s+([A-Za-z_][\w]*)", text)}


def _rename_rules(lines: list[str], notes: list[str]) -> None:
    clashes = sorted(_rule_names("\n".join(lines)) & RESERVED_V2)
    taken = _rule_names("\n".join(lines))
    for name in clashes:
        new = f"{name}_rule"
        while new in taken:
            new += "_"
        taken.add(new)
        pattern = _word(name)
        for i, line in enumerate(lines):
            if not line.startswith("#"):
                lines[i] = pattern.sub(new, line)
        notes.append(f"rule '{name}' renamed to '{new}' ('{name}' is a v2 keyword)")


def convert_to_v2(text: str) -> Conversion:
    """The v2 form of a v1 script (v2 scripts come back unchanged, with no notes)."""
    if detect_dialect(text) == 2:
        return Conversion(text, ())
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(newline)
    notes: list[str] = []
    _bake_substrings(lines, _defines(text), notes)
    _rename_rules(lines, notes)
    notes.insert(0, "added '#version 2'")
    return Conversion(newline.join([HEADER, *lines]), tuple(notes))
