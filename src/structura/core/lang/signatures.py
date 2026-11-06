"""Signature help (docs/12 §2.2): the v2 expression function around the cursor, or the transformation
operator whose arguments are being typed inside '{ … }' ('s ‹float› [‹float› ‹float›]'), with the index of
the argument being typed. Qt-free; the editor shows the result above the cursor."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .catalog import OperatorSpec, operator_names, operators

SIGNATURES: dict[str, tuple[tuple[str, ...], str]] = {
    "sin": (("degrees",), "Sine of an angle in degrees."),
    "cos": (("degrees",), "Cosine of an angle in degrees."),
    "tan": (("degrees",), "Tangent of an angle in degrees."),
    "asin": (("x",), "Arc sine, in degrees."),
    "acos": (("x",), "Arc cosine, in degrees."),
    "atan": (("x",), "Arc tangent, in degrees."),
    "atan2": (("y", "x"), "Angle of the vector (x, y), in degrees."),
    "sqrt": (("x",), "Square root."),
    "pow": (("base", "exponent"), "base raised to exponent."),
    "exp": (("x",), "e raised to x."),
    "log": (("x",), "Natural logarithm."),
    "abs": (("x",), "Absolute value."),
    "min": (("a", "b"), "The smaller value."),
    "max": (("a", "b"), "The larger value."),
    "floor": (("x",), "Largest integer ≤ x."),
    "ceil": (("x",), "Smallest integer ≥ x."),
    "round": (("x",), "Nearest integer."),
    "clamp": (("x", "lo", "hi"), "x limited to [lo, hi]."),
    "mix": (("a", "b", "t"), "Linear interpolation a + (b − a)·t."),
}
CONSTANTS: dict[str, str] = {"pi": "π ≈ 3.14159", "tau": "τ = 2π", "e": "Euler's number ≈ 2.71828"}
NAME_BEFORE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*$")


@dataclass(frozen=True)
class Signature:
    name: str
    params: tuple[str, ...]
    doc: str
    active: int  # index of the argument under the cursor
    kind: str = "function"  # "function" | "operator"
    arity: tuple[int, ...] = ()  # operator: allowed argument counts (optional trailing arguments)

    def parts(self) -> list[str]:
        """The parameters as displayed; operators mark optional ones with brackets."""
        if self.kind == "function":
            return list(self.params)
        first_optional = min((n for n in self.arity if n < len(self.params)), default=len(self.params))
        parts = [f"‹{p}›" for p in self.params]
        if first_optional < len(parts):  # one bracket around the optional tail: s ‹x› [‹y› ‹z›]
            parts[first_optional], parts[-1] = "[" + parts[first_optional], parts[-1] + "]"
        return parts

    @property
    def label(self) -> str:
        if self.kind == "function":
            return f"{self.name}({', '.join(self.params)})"
        return " ".join([self.name, *self.parts()])


def _open_call(line: str) -> tuple[int, int] | None:
    """(index of the unmatched '(', commas after it at depth 0) scanning back from the end of ``line``."""
    depth, commas = 0, 0
    for i in range(len(line) - 1, -1, -1):
        ch = line[i]
        if ch == ")":
            depth += 1
        elif ch == "(" and depth:
            depth -= 1
        elif ch == "(":
            return i, commas
        elif ch == "," and not depth:
            commas += 1
    return None


def _fits(word: str, kind: str) -> bool:
    """Can ``word`` be an argument of this type? Colours take names; numbers take numbers or '( … )'."""
    if kind.startswith("color"):
        return True
    return bool(re.fullmatch(r"[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?(/\d+)?|\(.*", word))


def _count_arguments(words: list[str]) -> tuple[str | None, int]:
    """The operator being given arguments and how many it has so far."""
    names, specs = operator_names(), _operator_specs()
    current, count = None, 0
    for word in words:
        spec = specs.get(current or "")
        canonical = names.get(word.lower())
        may_end = spec is None or count in spec.arity or count >= len(spec.args)
        if canonical is not None and may_end:
            current, count = canonical[0], 0
        elif spec is not None and count < len(spec.args) and _fits(word, spec.args[count]):
            count += 1
    return current, count


_BODY_HEADER = re.compile(r"(\brule\s+[\w:]+[^{}]*|^\s*(material|light|environment|camera|render)\b[^{}]*)$", re.M)


def _opens_a_body(before_brace: str) -> bool:
    """True when the brace ends 'rule NAME …' or a v2 block header rather than starting a transform list."""
    statement = re.split(r"[{}]", before_brace)[-1]
    return bool(_BODY_HEADER.search(statement))


def operator_signature(text: str, pos: int) -> Signature | None:
    """The operator whose arguments are being typed in the '{ … }' around ``pos``."""
    before = text[:pos]
    brace = before.rfind("{")
    if brace < 0 or "}" in before[brace:] or _opens_a_body(before[:brace]):
        return None
    segment = before[brace + 1 :]
    words = segment.split()
    done = words if not segment or segment[-1].isspace() else words[:-1]  # the last word is still being typed
    current, count = _count_arguments(done)
    spec = _operator_specs().get(current or "")
    if spec is None or count >= len(spec.args):
        return None
    return Signature(spec.name, spec.args, spec.doc, count, "operator", spec.arity)


def _operator_specs() -> dict[str, OperatorSpec]:
    return {o.name: o for o in operators()}


def _spec_args(name: str) -> int:
    spec = _operator_specs().get(name)
    return max(spec.arity) if spec else 0


def signature_at(text: str, pos: int) -> Signature | None:
    """The function call whose argument list contains ``pos`` (same line), else the operator being given
    arguments, or None."""
    line = text[text.rfind("\n", 0, pos) + 1 : pos]
    found = _open_call(line)
    if found is None:
        return operator_signature(text, pos)
    match = NAME_BEFORE.search(line[: found[0]])
    if match is None or match.group(1) not in SIGNATURES:
        return None
    params, doc = SIGNATURES[match.group(1)]
    return Signature(match.group(1), params, doc, min(found[1], len(params) - 1))
