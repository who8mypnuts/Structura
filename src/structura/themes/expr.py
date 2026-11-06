"""The derivation-expression language of roles.toml (docs/13 §4).

    expr := NAME | '#hex' | NUMBER | NAME '(' expr (',' expr)* ')'

NAME is a role ('ui.bg'), a palette entry ('nord8') or a function. Evaluation is lazy and memoised by the
caller through ``lookup``; cycles raise ``ThemeError``.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from ..core.color.oklab import from_oklch, mix, oklch

TOKEN = re.compile(r"\s*(#[0-9A-Fa-f]{3,8}|-?\d+(?:\.\d+)?|[A-Za-z_][\w.\-]*|[(),])")
Lookup = Callable[[str], str]


class ThemeError(ValueError):
    pass


def split_alpha(value: str) -> tuple[str, float]:
    v = value.lstrip("#")
    if len(v) == 8:
        return "#" + v[:6].upper(), int(v[6:], 16) / 255
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    return "#" + v.upper(), 1.0


def with_alpha(value: str, a: float) -> str:
    rgb, _ = split_alpha(value)
    return rgb if a >= 0.999 else f"{rgb}{round(max(0.0, a) * 255):02X}"


class Evaluator:
    def __init__(self, lookup: Lookup, dark: bool) -> None:
        self.lookup, self.dark = lookup, dark

    def evaluate(self, text: str) -> str:
        tokens = [t for t in TOKEN.findall(text) if t]
        value, rest = self._expr(tokens)
        if rest:
            raise ThemeError(f"trailing tokens in {text!r}")
        if not isinstance(value, str):
            raise ThemeError(f"{text!r} is a number, not a colour")
        return value

    def _expr(self, tokens: list[str]) -> tuple[str | float, list[str]]:
        if not tokens:
            raise ThemeError("unexpected end of expression")
        head, rest = tokens[0], tokens[1:]
        if head.startswith("#"):
            return with_alpha(*split_alpha(head)), rest
        if re.fullmatch(r"-?\d+(?:\.\d+)?", head):
            return float(head), rest
        if rest[:1] == ["("]:
            return self._call(head, rest[1:])
        return self.lookup(head), rest

    def _call(self, name: str, tokens: list[str]) -> tuple[str, list[str]]:
        args: list[str | float] = []
        while True:
            value, tokens = self._expr(tokens)
            args.append(value)
            if not tokens:
                raise ThemeError(f"unterminated call to {name}()")
            sep, tokens = tokens[0], tokens[1:]
            if sep == ")":
                return self._apply(name, args), tokens
            if sep != ",":
                raise ThemeError(f"expected ',' or ')' in {name}()")

    def _apply(self, name: str, args: list[str | float]) -> str:
        fn = FUNCTIONS.get(name)
        if fn is None:
            raise ThemeError(f"unknown function {name}()")
        return fn(self, *args)


def _colour(v: str | float) -> str:
    if not isinstance(v, str):
        raise ThemeError(f"expected a colour, got {v}")
    return v


def _mix(ev: Evaluator, a: str | float, b: str | float, t: str | float) -> str:
    (ca, aa), (cb, ab) = split_alpha(_colour(a)), split_alpha(_colour(b))
    return with_alpha(mix(ca, cb, float(t)), aa + (ab - aa) * float(t))


def _alpha(ev: Evaluator, a: str | float, t: str | float) -> str:
    return with_alpha(_colour(a), float(t))


def _deepen(ev: Evaluator, a: str | float, t: str | float) -> str:
    return _mix(ev, a, "#000000" if ev.dark else "#FFFFFF", t)


def _lch(a: str | float, fn: Callable[[float, float, float], tuple[float, float, float]]) -> str:
    rgb, alpha = split_alpha(_colour(a))
    return with_alpha(from_oklch(*fn(*oklch(rgb))), alpha)


def _chroma(ev: Evaluator, a: str | float, k: str | float) -> str:
    return _lch(a, lambda lum, c, h: (lum, c * float(k), h))


def _rotate(ev: Evaluator, a: str | float, deg: str | float) -> str:
    return _lch(a, lambda lum, c, h: (lum, max(c, 0.08), (h + float(deg)) % 360))


def _lift(ev: Evaluator, a: str | float, dl: str | float) -> str:
    sign = 1.0 if ev.dark else -1.0
    return _lch(a, lambda lum, c, h: (min(1.0, max(0.0, lum + sign * float(dl))), c, h))


FUNCTIONS: dict[str, Callable[..., str]] = {
    "mix": _mix,
    "alpha": _alpha,
    "deepen": _deepen,
    "chroma": _chroma,
    "rotate": _rotate,
    "lift": _lift,
}
