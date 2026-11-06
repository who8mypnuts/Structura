"""Theme authoring for the theme editor (docs/13 §8), Qt-free. A ThemeDraft is a theme *document*: the
author's values only; everything else is derived by the resolver. Built-in themes are read-only and are
duplicated into the user themes directory on save."""

from __future__ import annotations

import copy
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .derive import resolve_theme
from .loader import BUILTIN_DIR, builtin_ids, load_file, theme_ids, user_dir
from .model import Theme
from .writer import to_toml

DARK_BASE = ("#1C1F26", "#D5D9E0")  # (background, foreground) for 'start from accent'
LIGHT_BASE = ("#F7F7F5", "#24272E")
_ADJUSTED = re.compile(r"^([\w.]+): ")


def table_for(role: str) -> str:
    return "syntax" if role.startswith("syntax.") else "viewport" if role.startswith("viewport.") else "roles"


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "theme"


@dataclass
class ThemeDraft:
    data: dict[str, Any] = field(default_factory=dict)

    # -- construction ------------------------------------------------------------------------------------
    @classmethod
    def from_file(cls, path: Path) -> ThemeDraft:
        return cls(tomllib.loads(path.read_text(encoding="utf-8")))

    @classmethod
    def from_id(cls, theme_id: str) -> ThemeDraft:
        user = user_dir() / f"{theme_id}.toml"
        return cls.from_file(user if user.exists() else BUILTIN_DIR / f"{theme_id}.toml")

    @classmethod
    def from_accent(cls, name: str, accent: str, dark: bool) -> ThemeDraft:
        bg, fg = DARK_BASE if dark else LIGHT_BASE
        meta = {"id": slug(name), "name": name, "kind": "dark" if dark else "light", "author": "", "license": ""}
        return cls({"meta": meta, "roles": {"ui.bg": bg, "ui.fg": fg, "ui.accent": accent, "editor.bg": bg}})

    # -- reading -----------------------------------------------------------------------------------------
    @property
    def id(self) -> str:
        return str(self.data.get("meta", {}).get("id", ""))

    @property
    def read_only(self) -> bool:
        return self.id in builtin_ids() and not (user_dir() / f"{self.id}.toml").exists()

    def theme(self) -> Theme:
        return resolve_theme(self.data)

    def override(self, role: str) -> str | None:
        """The author's value for ``role`` (None when the role is derived)."""
        value = self.data.get(table_for(role), {}).get(role)
        return str(value["color"]) if isinstance(value, dict) else (None if value is None else str(value))

    # -- editing -----------------------------------------------------------------------------------------
    def set_role(self, role: str, color: str) -> None:
        table = self.data.setdefault(table_for(role), {})
        current = table.get(role)
        table[role] = {**current, "color": color} if isinstance(current, dict) else color

    def reset_role(self, role: str) -> None:
        self.data.get(table_for(role), {}).pop(role, None)

    def flag(self, role: str, flag: str) -> bool:
        value = self.data.get("syntax", {}).get(role)
        return bool(value.get(flag, False)) if isinstance(value, dict) else False

    def set_flag(self, role: str, flag: str, on: bool) -> None:
        table = self.data.setdefault("syntax", {})
        current = table.get(role)
        entry = dict(current) if isinstance(current, dict) else {"color": current or self.theme()[role]}
        entry[flag] = on
        table[role] = entry

    def contrast_fixes(self) -> dict[str, str]:
        """Roles the resolver had to adjust for contrast, with the colour it chose."""
        theme = self.theme()
        return {m.group(1): theme[m.group(1)] for line in theme.adjustments if (m := _ADJUSTED.match(line))}

    def fix_contrast(self) -> int:
        """Write the resolver's contrast fixes into the document; returns how many roles changed."""
        fixes = self.contrast_fixes()
        for role, color in fixes.items():
            self.set_role(role, color)
        return len(fixes)

    # -- files -------------------------------------------------------------------------------------------
    def duplicate(self, name: str) -> ThemeDraft:
        copy_data = copy.deepcopy(self.data)
        meta = copy_data.setdefault("meta", {})
        taken = set(theme_ids())
        base = slug(name)
        theme_id, n = base, 2
        while theme_id in taken:
            theme_id, n = f"{base}-{n}", n + 1
        meta.update({"id": theme_id, "name": name, "pair": ""})
        return ThemeDraft(copy_data)

    def save(self, directory: Path | None = None) -> Path:
        if self.read_only and directory is None:
            raise PermissionError(f"'{self.id}' is a built-in theme: duplicate it first")
        folder = directory or user_dir()
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{self.id}.toml"
        path.write_text(to_toml(self.data, f"{self.data['meta'].get('name', self.id)} — edited in Structura"))
        load_file(path)  # validate by resolving what was written
        return path


def delete_user_theme(theme_id: str) -> bool:
    path = user_dir() / f"{theme_id}.toml"
    if not path.exists():
        return False
    path.unlink()
    return True
