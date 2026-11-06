"""Keymaps (docs/14 §4.2): presets from keymaps.toml plus the user's own bindings, applied to the
CommandRegistry. Stored in settings as 'keymap/preset' and 'keymap/overrides' (JSON: id → shortcut)."""

from __future__ import annotations

import json
import tomllib
from functools import cache
from pathlib import Path

from PySide6.QtGui import QKeySequence

from ...services.settings import SettingsService
from .registry import CommandRegistry

PRESETS_FILE = Path(__file__).with_name("keymaps.toml")
DEFAULT_PRESET = "structura"
PRESET_TITLES = {"structura": "Structura", "legacy": "Legacy (Structure Synth 1.5)", "vscode": "VS Code-like"}


@cache
def presets() -> dict[str, dict[str, str]]:
    with PRESETS_FILE.open("rb") as fh:
        return {name: {str(k): str(v) for k, v in table.items()} for name, table in tomllib.load(fh).items()}


def normal(shortcut: str) -> str:
    """The portable text of a shortcut ('ctrl+shift+p' → 'Ctrl+Shift+P')."""
    return QKeySequence(shortcut).toString() if shortcut else ""


class Keymap:
    def __init__(self, registry: CommandRegistry, settings: SettingsService) -> None:
        self.registry, self.settings = registry, settings

    @property
    def preset(self) -> str:
        name = str(self.settings.value("keymap/preset", DEFAULT_PRESET))
        return name if name in presets() else DEFAULT_PRESET

    def overrides(self) -> dict[str, str]:
        try:
            data = json.loads(str(self.settings.value("keymap/overrides", "{}")))
        except json.JSONDecodeError:
            return {}
        return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}

    def default(self, command_id: str, preset: str | None = None) -> str:
        """The binding before the user's own: the preset's, else the command's default."""
        table = presets().get(preset or self.preset, {})
        return normal(table.get(command_id, self.registry.command(command_id).shortcut))

    def effective(self, preset: str | None = None, overrides: dict[str, str] | None = None) -> dict[str, str]:
        own = self.overrides() if overrides is None else overrides
        return {
            c.id: normal(own[c.id]) if c.id in own else self.default(c.id, preset) for c in self.registry.commands()
        }

    def conflicts(self, bindings: dict[str, str]) -> dict[str, list[str]]:
        """Shortcut → the commands that share it (only shortcuts used more than once)."""
        users: dict[str, list[str]] = {}
        for command_id, shortcut in bindings.items():
            if shortcut:
                users.setdefault(shortcut, []).append(command_id)
        return {s: ids for s, ids in users.items() if len(ids) > 1}

    def save(self, preset: str, overrides: dict[str, str]) -> None:
        self.settings.set_value("keymap/preset", preset)
        self.settings.set_value("keymap/overrides", json.dumps(overrides, sort_keys=True))
        self.apply()

    def apply(self) -> None:
        for command_id, shortcut in self.effective().items():
            self.registry.action(command_id).setShortcut(QKeySequence(shortcut))
