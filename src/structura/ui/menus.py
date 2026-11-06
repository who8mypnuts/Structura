"""Build the menu bar from the command registry (no hand-made duplicate actions; docs/14 §4)."""

from __future__ import annotations

from PySide6.QtWidgets import QMenu, QMenuBar

from .commands.registry import CommandRegistry

MENU_ORDER = ("File", "Edit", "Insert", "View", "Build", "Render", "Export", "Help")


def build_menus(bar: QMenuBar, registry: CommandRegistry) -> None:
    bar.clear()
    by_menu: dict[str, list[tuple[int, str]]] = {}
    for order, command in enumerate(registry.commands()):
        if command.menu:
            by_menu.setdefault(command.menu, []).append((command.group * 10_000 + order, command.id))
    for title in (*MENU_ORDER, *sorted(set(by_menu) - set(MENU_ORDER))):
        entries = sorted(by_menu.get(title, []))
        if not entries:
            continue
        menu = bar.addMenu(f"&{title}")
        submenus: dict[str, QMenu] = {}
        last_group = None
        for key, command_id in entries:
            group = key // 10_000
            if last_group is not None and group != last_group:
                menu.addSeparator()
            sub = registry.command(command_id).submenu
            if sub and sub not in submenus:
                submenus[sub] = menu.addMenu(sub)
            (submenus[sub] if sub else menu).addAction(registry.action(command_id))
            last_group = group
