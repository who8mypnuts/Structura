"""E015, typed parameters (docs/05 §9.2): a '#param' whose default does not fit its type or range, and a
parameter used where its type does not fit — a colour or a switch where a transformation needs a number, or a
number after 'color'. Checked on the edited text, so the spans point at the declaration or the use."""

from __future__ import annotations

import re

from ...color import parse_color
from ..diagnostics import Diagnostic, diagnostic
from ..highlight import lex_line
from ..source import Span

PARAM = re.compile(
    r"^\s*#param\s+(?P<name>[A-Za-z_]\w*)\s+(?P<kind>float|int|color|bool|enum)\s*=\s*(?P<default>\S+)"
    r"(?:\s+range\s+(?P<low>-?[\d.]+)\.\.(?P<high>-?[\d.]+))?(?:\s+of\s+(?P<choices>\S+))?"
)
NUMERIC = {"float", "int"}
COLOR_OPERATORS = {"color", "blend"}  # their first argument is a colour


def _number(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:
        return None


def _declaration_problem(m: re.Match[str]) -> str | None:
    kind, default = m["kind"], m["default"]
    value = _number(default)
    if kind in NUMERIC and (value is None or (kind == "int" and not value.is_integer())):
        return f"'{default}' is not {'an integer' if kind == 'int' else 'a number'}"
    if kind in NUMERIC and m["low"] is not None and value is not None:
        low, high = float(m["low"]), float(m["high"])
        if not low <= value <= high:
            return f"{default} is outside its range {m['low']}..{m['high']}"
    if kind == "color" and parse_color(default) is None:
        return f"'{default}' is not a colour"
    if kind == "bool" and default not in ("true", "false"):
        return f"'{default}' is not true or false"
    if kind == "enum" and m["choices"] and default not in m["choices"].split("|"):
        return f"'{default}' is not one of {m['choices']}"
    return None


def _declarations(text: str) -> tuple[dict[str, str], list[Diagnostic]]:
    kinds, problems, offset = {}, [], 0
    for line in text.split("\n"):
        m = PARAM.match(line)
        if m:
            kinds[m["name"]] = m["kind"]
            problem = _declaration_problem(m)
            if problem:
                span = Span(offset + m.start("default"), offset + m.end("default"))
                problems.append(diagnostic("E015", f"#param {m['name']}: {problem}", span))
        offset += len(line) + 1
    return kinds, problems


def _uses(text: str, kinds: dict[str, str]) -> list[Diagnostic]:
    """A parameter right after a transformation operator whose argument has the other type."""
    problems, offset, state = [], 0, 0
    for line in text.split("\n"):
        tokens, state = lex_line(line, state)
        previous = ""
        for start, length, role in tokens:
            word = line[start : start + length]
            kind = kinds.get(word)
            if kind is not None and previous:
                wants_color = previous in COLOR_OPERATORS
                if wants_color != (kind == "color"):
                    need = "a colour" if wants_color else "a number"
                    message = f"'{word}' is a {kind} parameter; '{previous}' needs {need} here"
                    problems.append(diagnostic("E015", message, Span(offset + start, offset + start + length)))
            previous = word if role == "operator" and word not in "*" else ""
        offset += len(line) + 1
    return problems


def param_diagnostics(text: str) -> list[Diagnostic]:
    kinds, problems = _declarations(text)
    return problems + (_uses(text, kinds) if kinds else [])
