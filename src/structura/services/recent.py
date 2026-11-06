"""Recently opened files (docs/14 §4.1 'Open Recent'): most recent first, existing files only."""

from __future__ import annotations

import json
from pathlib import Path

from .settings import SettingsService

KEY, LIMIT = "files/recent", 12


class RecentFiles:
    def __init__(self, settings: SettingsService) -> None:
        self.settings = settings

    def _stored(self) -> list[str]:
        try:
            data = json.loads(str(self.settings.value(KEY, "[]")))
        except json.JSONDecodeError:
            return []
        return [str(p) for p in data] if isinstance(data, list) else []

    def paths(self) -> list[Path]:
        return [Path(p) for p in self._stored() if Path(p).is_file()]

    def add(self, path: Path) -> None:
        name = str(path.resolve())
        entries = [name, *(p for p in self._stored() if p != name)][:LIMIT]
        self.settings.set_value(KEY, json.dumps(entries))
        self.settings.set_value("files/last", name)

    def clear(self) -> None:
        self.settings.set_value(KEY, "[]")
