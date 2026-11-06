"""Resolved theme objects (docs/13 §2–3). Colours are '#RRGGBB' or '#RRGGBBAA' strings."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SyntaxStyle:
    color: str
    bold: bool = False
    italic: bool = False
    underline: bool = False


@dataclass(frozen=True)
class ThemeMeta:
    id: str
    name: str
    kind: str  # "dark" | "light"
    family: str = ""
    author: str = ""
    license: str = ""
    pair: str = ""  # counterpart for "follow system appearance"

    @property
    def dark(self) -> bool:
        return self.kind == "dark"


@dataclass(frozen=True)
class Theme:
    meta: ThemeMeta
    colors: dict[str, str]  # every role in roles.toml, resolved
    syntax: dict[str, SyntaxStyle]  # every syntax.* role
    adjustments: tuple[str, ...] = field(default=())  # contrast fixes applied (for 'structura theme check')

    def __getitem__(self, role: str) -> str:
        return self.colors[role]

    def style(self, role: str) -> SyntaxStyle:
        return self.syntax[role]
