"""One CommandRegistry feeds the menus, tool buttons, shortcuts and the command palette (docs/14 §4)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QWidget


@dataclass(frozen=True)
class Command:
    id: str  # "build.run"
    title: str
    handler: Callable[[], object]
    shortcut: str = ""
    menu: str = ""  # top-level menu title; "" = palette only
    group: int = 0  # separators between groups inside a menu
    checkable: bool = False
    checked: Callable[[], bool] | None = None
    enabled: Callable[[], bool] | None = None
    tip: str = ""
    submenu: str = ""  # optional submenu inside ``menu``

    @property
    def category(self) -> str:
        return self.id.split(".", 1)[0].title()


class CommandRegistry(QObject):
    changed = Signal()

    def __init__(self, host: QWidget) -> None:
        super().__init__(host)
        self.host = host
        self._commands: dict[str, Command] = {}
        self._actions: dict[str, QAction] = {}

    def register(self, command: Command) -> QAction:
        if command.id in self._commands:
            raise ValueError(f"command {command.id!r} registered twice")
        action = QAction(command.title, self.host)
        action.setObjectName(command.id)
        if command.shortcut:
            action.setShortcut(QKeySequence(command.shortcut))
        action.setCheckable(command.checkable)
        action.setToolTip(command.tip or command.title)
        action.triggered.connect(lambda _checked=False, c=command: self._run(c))
        self.host.addAction(action)  # shortcuts work even when the command is in no menu
        self._commands[command.id], self._actions[command.id] = command, action
        self.changed.emit()
        return action

    def _run(self, command: Command) -> None:
        if command.enabled is None or command.enabled():
            command.handler()
        self.refresh()

    def action(self, command_id: str) -> QAction:
        return self._actions[command_id]

    def command(self, command_id: str) -> Command:
        return self._commands[command_id]

    def commands(self) -> list[Command]:
        return list(self._commands.values())

    def trigger(self, command_id: str) -> None:
        self._actions[command_id].trigger()

    def refresh(self) -> None:
        """Re-evaluate enablement and check state (cheap predicates)."""
        for cid, command in self._commands.items():
            action = self._actions[cid]
            if command.enabled is not None:
                action.setEnabled(command.enabled())
            if command.checked is not None:
                action.setChecked(command.checked())
