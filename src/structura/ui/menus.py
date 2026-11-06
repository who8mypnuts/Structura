"""Build the menu bar from the command registry (no hand-made duplicate actions; docs/14 §4)."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QMenu, QMenuBar

from .commands.registry import CommandRegistry
from .i18n import tr

MENU_ORDER = ("File", "Edit", "Insert", "View", "Build", "Render", "Export", "Help")


def _top_menu(bar: QMenuBar, title: str) -> QMenu:
    for action in bar.actions():
        menu = action.menu()
        if isinstance(menu, QMenu) and action.text().replace("&", "") == tr(title, "Menus"):
            return menu
    raise KeyError(title)


def add_dynamic_menu(bar: QMenuBar, top: str, title: str, after: str, fill: Callable[[QMenu], None]) -> QMenu:
    """A submenu filled when it opens (e.g. File ▸ Open Recent), placed after the action named ``after``."""
    menu = _top_menu(bar, top)
    submenu = QMenu(tr(title, "Menus"), menu)
    submenu.aboutToShow.connect(lambda: fill(submenu))
    actions = menu.actions()
    index = next((i for i, a in enumerate(actions) if a.objectName() == after), len(actions) - 1)
    if index + 1 < len(actions):
        menu.insertMenu(actions[index + 1], submenu)
    else:
        menu.addMenu(submenu)
    return submenu


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
        menu = bar.addMenu("&" + tr(title, "Menus"))
        submenus: dict[str, QMenu] = {}
        last_group = None
        for key, command_id in entries:
            group = key // 10_000
            if last_group is not None and group != last_group:
                menu.addSeparator()
            sub = registry.command(command_id).submenu
            if sub and sub not in submenus:
                submenus[sub] = menu.addMenu(tr(sub, "Menus"))
            (submenus[sub] if sub else menu).addAction(registry.action(command_id))
            last_group = group
