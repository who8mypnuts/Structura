"""Command palette (Ctrl+Shift+P): fuzzy search over every enabled command (docs/14 §4)."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QWidget

from .commands.registry import CommandRegistry
from .i18n import tr
from .picker import Entry, PickerPopup, fuzzy_score, ranked

__all__ = ["CommandPalette", "fuzzy_score"]


class CommandPalette(PickerPopup):
    placeholder = "Type a command"

    def __init__(self, registry: CommandRegistry, parent: QWidget) -> None:
        self.registry = registry
        super().__init__(parent)

    def entries(self, query: str) -> list[Entry]:
        commands = sorted(self.registry.commands(), key=lambda c: c.label)
        entries = [(f"{tr(c.category, 'Menus')}: {c.label}", self.registry.action(c.id).shortcut().toString(), c.id)
                   for c in commands if self.registry.action(c.id).isEnabled()]  # fmt: skip
        return ranked(query, entries)

    def activate(self, payload: Any) -> None:
        self.registry.trigger(str(payload))
