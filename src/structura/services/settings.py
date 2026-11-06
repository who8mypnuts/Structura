"""SettingsService: typed application preferences over QSettings (docs/02 §6.7)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QSettings, QStandardPaths, Signal


class SettingsService(QObject):
    changed = Signal(str, object)

    def __init__(self, path: Path | None = None) -> None:
        super().__init__()
        self._path = path
        if path is None:
            self._qs = QSettings("Structura", "Structura")
        else:
            self._qs = QSettings(str(path), QSettings.Format.IniFormat)

    def directory(self) -> Path:
        """Where per-user files live (session, recovery): next to an explicit settings file, otherwise the
        platform's application-data folder."""
        if self._path is not None:
            return self._path.parent
        return Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))

    def value(self, key: str, default: Any = None) -> Any:
        value = self._qs.value(key, default)
        if isinstance(default, bool) and isinstance(value, str):
            return value.lower() in ("true", "1")
        if isinstance(default, int) and not isinstance(default, bool) and isinstance(value, str):
            return int(value)
        if isinstance(default, float) and isinstance(value, str):
            return float(value)
        return value

    def set_value(self, key: str, value: Any) -> None:
        if self._qs.value(key) == value:
            return
        self._qs.setValue(key, value)
        self.changed.emit(key, value)

    def sync(self) -> None:
        self._qs.sync()
