"""Theme resolution: author values + derivation rules + contrast enforcement (docs/13 §4)."""

from __future__ import annotations

import tomllib
from functools import cache
from pathlib import Path
from typing import Any

from ..core.color.oklab import contrast, from_oklch, oklch
from .expr import Evaluator, ThemeError, split_alpha
from .model import SyntaxStyle, Theme, ThemeMeta

ROLES_FILE = Path(__file__).resolve().parent / "roles.toml"
STYLE_FLAGS = ("bold", "italic", "underline")


@cache
def catalogue() -> tuple[dict[str, Any], tuple[tuple[str, str, float], ...]]:
    """(role → derivation expression or {'required': True}, contrast pairs)."""
    data = tomllib.loads(ROLES_FILE.read_text(encoding="utf-8"))
    pairs = tuple((fg, bg, float(r)) for fg, bg, r in data.pop("contrast")["pairs"])
    roles: dict[str, Any] = {}
    for group in data.values():
        roles.update(group)
    return roles, pairs


def role_names() -> list[str]:
    return list(catalogue()[0])


@cache
def role_groups() -> dict[str, list[str]]:
    """The roles grouped as in roles.toml (ui, status, bars, editor, syntax, diag, viewport, render, chart)."""
    data = tomllib.loads(ROLES_FILE.read_text(encoding="utf-8"))
    data.pop("contrast", None)
    return {group: list(roles) for group, roles in data.items()}


def _author_values(data: dict[str, Any]) -> tuple[dict[str, str], dict[str, dict[str, bool]]]:
    """Colour expressions and syntax flags from the theme's [roles], [syntax] and [viewport] tables."""
    values: dict[str, str] = {}
    flags: dict[str, dict[str, bool]] = {}
    for table in ("roles", "syntax", "viewport"):
        for role, value in data.get(table, {}).items():
            if isinstance(value, dict):
                values[role] = str(value["color"])
                flags[role] = {k: bool(value[k]) for k in STYLE_FLAGS if k in value}
            else:
                values[role] = str(value)
    return values, flags


class _Resolver:
    def __init__(self, values: dict[str, str], palette: dict[str, str], dark: bool) -> None:
        self.values, self.palette = values, palette
        self.rules, _ = catalogue()
        self.resolved: dict[str, str] = {}
        self.active: set[str] = set()
        self.evaluator = Evaluator(self.lookup, dark)

    def lookup(self, name: str) -> str:
        if name in self.resolved:
            return self.resolved[name]
        if name in self.active:
            raise ThemeError(f"derivation cycle through '{name}'")
        self.active.add(name)
        self.resolved[name] = self.evaluator.evaluate(self._source(name))
        self.active.discard(name)
        return self.resolved[name]

    def _source(self, name: str) -> str:
        if name in self.values:
            return self.values[name]
        rule = self.rules.get(name)
        if isinstance(rule, str):
            return rule
        if isinstance(rule, dict):
            raise ThemeError(f"required role '{name}' is missing")
        if name in self.palette:
            return self.palette[name]
        raise ThemeError(f"unknown role or palette colour '{name}'")


def _walk(fg: str, bg: str, minimum: float, step: float) -> str | None:
    lum, c, h = oklch(fg)
    for _ in range(101):
        candidate = from_oklch(lum, c, h)
        if contrast(candidate, bg) >= minimum:
            return candidate
        if not 0.0 < lum < 1.0:
            return None
        lum = min(1.0, max(0.0, lum + step))
    return None


def _fix_contrast(fg: str, bg: str, minimum: float, dark: bool) -> str:
    """Move fg's OKLCH lightness away from bg until the WCAG ratio passes (flipping sides if it must)."""
    lum, bg_lum = oklch(fg)[0], oklch(bg)[0]
    up = lum > bg_lum if abs(lum - bg_lum) > 0.02 else dark
    for step in (0.01, -0.01) if up else (-0.01, 0.01):
        fixed = _walk(fg, bg, minimum, step)
        if fixed is not None:
            return fixed
    return "#FFFFFF" if contrast("#FFFFFF", bg) > contrast("#000000", bg) else "#000000"


def _enforce(colors: dict[str, str], dark: bool) -> list[str]:
    fixes = []
    for fg, bg, minimum in catalogue()[1]:
        (f, fa), (b, ba) = split_alpha(colors[fg]), split_alpha(colors[bg])
        if fa < 1 or ba < 1 or contrast(f, b) >= minimum:
            continue
        colors[fg] = _fix_contrast(f, b, minimum, dark)
        fixes.append(f"{fg}: {f} → {colors[fg]} ({contrast(f, b):.2f} → {contrast(colors[fg], b):.2f} on {bg})")
    return fixes


def resolve_theme(data: dict[str, Any]) -> Theme:
    meta_data = data.get("meta", {})
    meta = ThemeMeta(**{k: str(v) for k, v in meta_data.items()})
    values, flags = _author_values(data)
    palette = {k: str(v) for k, v in data.get("palette", {}).items()}
    resolver = _Resolver(values, palette, meta.dark)
    colors = {role: resolver.lookup(role) for role in role_names()}
    fixes = _enforce(colors, meta.dark)
    syntax = {role: SyntaxStyle(colors[role], **flags.get(role, {})) for role in colors if role.startswith("syntax.")}
    return Theme(meta, colors, syntax, tuple(fixes))
