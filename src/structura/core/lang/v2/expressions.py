"""Compile-time expressions '( expr )' (docs/05 §9.1), evaluated once, after define substitution.

Allowed: numbers, + − * / % ^ (power), unary minus, parentheses, the constants pi/tau/e and the functions
sin cos tan asin acos atan atan2 (degrees, like 'rx'), sqrt pow exp log abs min max clamp floor ceil
round mix. Comments, '#' lines and '[…]' arguments are left alone.
"""

from __future__ import annotations

import ast
import math
import operator
import re
from collections.abc import Callable
from typing import Any

from ..diagnostics import ParseError
from ..source import Span

DEG = math.pi / 180.0
FUNCTIONS: dict[str, Callable[..., float]] = {
    "sin": lambda a: math.sin(a * DEG), "cos": lambda a: math.cos(a * DEG), "tan": lambda a: math.tan(a * DEG),
    "asin": lambda a: math.asin(a) / DEG, "acos": lambda a: math.acos(a) / DEG, "atan": lambda a: math.atan(a) / DEG,
    "atan2": lambda y, x: math.atan2(y, x) / DEG, "sqrt": math.sqrt, "pow": math.pow, "exp": math.exp,
    "log": math.log, "abs": abs, "min": min, "max": max, "floor": math.floor, "ceil": math.ceil, "round": round,
    "clamp": lambda x, a, b: min(max(x, a), b), "mix": lambda a, b, t: a + (b - a) * t,
}  # fmt: skip
CONSTANTS = {"pi": math.pi, "tau": math.tau, "e": math.e}
BINARY: dict[type, Callable[[Any, Any], Any]] = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
}  # fmt: skip


def _eval(node: ast.AST, names: dict[str, float]) -> float:
    if isinstance(node, ast.Expression):
        return _eval(node.body, names)
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub | ast.UAdd):
        value = _eval(node.operand, names)
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.BinOp) and type(node.op) in BINARY:
        return float(BINARY[type(node.op)](_eval(node.left, names), _eval(node.right, names)))
    if isinstance(node, ast.Name) and node.id in {**CONSTANTS, **names}:
        return {**CONSTANTS, **names}[node.id]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FUNCTIONS:
        return float(FUNCTIONS[node.func.id](*(_eval(a, names) for a in node.args)))
    raise ValueError(f"unsupported expression element: {ast.unparse(node)}")


def evaluate(expr: str, names: dict[str, float] | None = None) -> float:
    tree = ast.parse(expr.replace("^", "**"), mode="eval")
    return _eval(tree, names or {})


def format_value(value: float) -> str:
    return f"{value:.10g}"


def _groups(line: str) -> list[tuple[int, int]]:
    """Outermost '( … )' spans outside comments and '[…]'."""
    spans, depth, start, bracket = [], 0, -1, False
    for i, ch in enumerate(line):
        if line.startswith("//", i) and depth == 0:
            break
        bracket = bracket or ch == "["
        bracket = bracket and ch != "]"
        if bracket:
            continue
        if ch == "(":
            start, depth = (i if depth == 0 else start), depth + 1
        elif ch == ")" and depth:
            depth -= 1
            if depth == 0:
                spans.append((start, i + 1))
    return spans


def substitute_expressions(text: str, names: dict[str, float] | None = None) -> str:
    lines, offset = [], 0
    for original in text.split("\n"):
        line = original
        if not line.lstrip().startswith("#"):
            for start, end in reversed(_groups(original)):
                try:
                    value = format_value(evaluate(original[start + 1 : end - 1], names))
                except (ValueError, SyntaxError, ZeroDivisionError, TypeError, OverflowError) as exc:
                    raise ParseError(f"Expression error: {exc}", Span(offset + start, offset + end), "E016") from exc
                line = line[:start] + value + line[end:]
        lines.append(line)
        offset += len(original) + 1
    return "\n".join(lines)


PARAM = re.compile(
    r"^(\s*)#param\s+([A-Za-z_]\w*)\s+(float|int|color|bool|enum)\s*=\s*(\S+)"
    r'(?:\s+range\s+(-?[\d.]+)\.\.(-?[\d.]+))?(?:\s+of\s+(\S+))?(?:\s+"([^"]*)")?\s*$'
)


def params_to_defines(text: str) -> str:
    """'#param NAME float = 20 range 0..90 "label"' → '#define NAME 20 (float:0-90)' (slider in the UI)."""
    out = []
    for line in text.split("\n"):
        m = PARAM.match(line)
        if m is None:
            out.append(line)
            continue
        pad, name, kind, default, low, high, choices, _label = m.groups()
        control = f" ({kind}:{low}-{high})" if kind in ("float", "int") and low is not None else ""
        control = f" ({kind})" if kind in ("color", "bool") else control
        control = f" (enum:{choices})" if kind == "enum" and choices else control
        out.append(f"{pad}#define {name} {default}{control}")
    return "\n".join(out)
