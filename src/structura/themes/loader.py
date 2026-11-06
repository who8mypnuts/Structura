"""Finding and loading themes: built-ins (package data) and the user themes directory (docs/13 §3)."""

from __future__ import annotations

import tomllib
from functools import cache
from pathlib import Path

import platformdirs

from .derive import resolve_theme
from .model import Theme

BUILTIN_DIR = Path(__file__).resolve().parent / "builtin"
DEFAULT_THEME = "structura-dark"


def user_dir() -> Path:
    return Path(platformdirs.user_data_dir("structura")) / "themes"


def _files() -> dict[str, Path]:
    found = {p.stem: p for p in sorted(BUILTIN_DIR.glob("*.toml"))}
    if user_dir().is_dir():
        found |= {p.stem: p for p in sorted(user_dir().glob("*.toml"))}  # user themes may shadow built-ins
    return found


def theme_ids() -> list[str]:
    return sorted(_files())


def builtin_ids() -> list[str]:
    return sorted(p.stem for p in BUILTIN_DIR.glob("*.toml"))


def load_file(path: Path) -> Theme:
    return resolve_theme(tomllib.loads(path.read_text(encoding="utf-8")))


@cache
def _load_cached(path: Path, mtime: float) -> Theme:
    return load_file(path)


def load_theme(theme_id: str) -> Theme:
    """The theme with this id, falling back to the default if it does not exist."""
    files = _files()
    path = files.get(theme_id) or files[DEFAULT_THEME]
    return _load_cached(path, path.stat().st_mtime)
