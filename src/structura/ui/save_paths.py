"""Where Save As dialogs start (docs/14 §7 "Paths"): never the program's working directory.

Each kind of output (exports, renders, reports, animations) remembers the folder it was last saved to. The
first time, it starts next to the script (if the script is saved) or in a "Structura" folder under the
user's Documents or Pictures. File names are suggested from the script's name.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import platformdirs
from PySide6.QtWidgets import QFileDialog, QWidget

PICTURES = ("render", "animation")  # kinds that default to the Pictures folder


class Settings(Protocol):
    def value(self, key: str, default: object = None) -> object: ...

    def set_value(self, key: str, value: object) -> None: ...


def default_folder(kind: str) -> Path:
    base = platformdirs.user_pictures_dir() if kind in PICTURES else platformdirs.user_documents_dir()
    return Path(base) / "Structura"


class SavePaths:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def folder(self, kind: str, script: Path | None = None) -> Path:
        """The last folder used for ``kind``, else the script's folder, else the default folder (Preferences ▸
        Default folder, or Documents/Structura)."""
        last = self.settings.value(f"paths/{kind}", "")
        if isinstance(last, str) and last and Path(last).is_dir():
            return Path(last)
        if script is not None and script.parent.is_dir():
            return script.parent
        chosen = self.settings.value("paths/output", "")
        return Path(chosen) if isinstance(chosen, str) and chosen else default_folder(kind)

    def suggest(self, kind: str, name: str, script: Path | None = None) -> Path:
        """An absolute path for a new file called ``name`` (a stem plus extension)."""
        return self.folder(kind, script) / name

    def remember(self, kind: str, path: Path) -> None:
        self.settings.set_value(f"paths/{kind}", str(path.parent))

    def ask(
        self, parent: QWidget, kind: str, title: str, suggestion: Path, filters: list[str], selected: str = ""
    ) -> tuple[Path, str] | None:
        """The native Save As dialog, starting at ``suggestion``; (chosen path, chosen filter) or None.

        The default folder is created on demand, so the dialog can open inside it.
        """
        if suggestion.parent in (default_folder(kind), self.folder(kind)) and not suggestion.parent.exists():
            suggestion.parent.mkdir(parents=True, exist_ok=True)  # the default folder is created on demand
        name, chosen = QFileDialog.getSaveFileName(parent, title, str(suggestion), ";;".join(filters), selected)
        if not name:
            return None
        path = Path(name)
        self.remember(kind, path)
        return path, chosen


def with_extension(path: Path, extensions: tuple[str, ...]) -> Path:
    """``path`` with the format's first extension added when it has none of them (typed without one)."""
    if path.suffix.lower() in extensions:
        return path
    return path.with_name(path.name + extensions[0])


def stem_for(script: Path | None, fallback: str = "structure") -> str:
    return script.stem if script is not None else fallback
