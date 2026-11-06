"""The built-in commands (docs/14 §4.1–4.2). Handlers call into the main window; nothing else builds QActions."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from ...core.lang.catalog import snippets
from .registry import Command, CommandRegistry

if TYPE_CHECKING:
    from ..app_window import MainWindow

Predicate = Callable[[], bool]


def _file_edit(w: MainWindow, has_tab: Predicate) -> list[Command]:
    d = w.docs
    return [
        Command("file.new", "New Script", d.new_script, "Ctrl+N", "File", 0),
        Command("file.open", "Open…", d.open_dialog, "Ctrl+O", "File", 0),
        Command("file.save", "Save", d.save, "Ctrl+S", "File", 1, enabled=has_tab),
        Command("file.save_as", "Save As…", d.save_as, "Ctrl+Shift+S", "File", 1, enabled=has_tab),
        Command("file.close", "Close Tab", d.close_tab, "Ctrl+W", "File", 1, enabled=has_tab),
        Command("file.preferences", "Preferences…", w.preferences, "Ctrl+,", "File", 8),
        Command("file.quit", "Quit", w.close, "Ctrl+Q", "File", 9),
        Command("edit.find", "Find…", lambda: d.open_find(False), "Ctrl+F", "Edit", 0, enabled=has_tab),
        Command("edit.replace", "Replace…", lambda: d.open_find(True), "Ctrl+H", "Edit", 0, enabled=has_tab),
        Command("edit.comment", "Toggle Line Comment", d.toggle_comment, "", "Edit", 1, enabled=has_tab),
        Command("edit.definition", "Go to Definition", d.definition_under_cursor, "F12", "Edit", 1, enabled=has_tab),
        Command("edit.rename", "Rename Rule…", d.rename_rule, "F2", "Edit", 1, enabled=has_tab),
        Command("edit.references", "Find References", d.find_references, "Shift+F12", "Edit", 1, enabled=has_tab),
        Command("edit.format", "Format Document", d.format_document, "Shift+Alt+F", "Edit", 1, enabled=has_tab),
        Command("edit.zoom_in", "Zoom In", lambda: d.zoom(1), "Ctrl+=", "Edit", 2, enabled=has_tab),
        Command("edit.zoom_out", "Zoom Out", lambda: d.zoom(-1), "Ctrl+-", "Edit", 2, enabled=has_tab),
    ]


def _view_build_render(w: MainWindow, has_tab: Predicate) -> list[Command]:
    live = Command(
        "build.live", "Live Build", w.toggle_live, menu="Build", checkable=True,
        checked=lambda: w.workbench.live, tip="Rebuild while typing",
    )  # fmt: skip
    return [
        Command("view.palette", "Command Palette", w.command_palette.open, "Ctrl+Shift+P", "View", 0),
        Command("view.frame_all", "Frame All", w.viewport.frame_all, "", "View", 1, tip="Frame the structure"),
        Command("view.look_studio", "Look: Studio", lambda: w.set_look("studio"), "", "View", 2),
        Command("view.look_legacy", "Look: Legacy", lambda: w.set_look("legacy"), "", "View", 2),
        Command("view.look_clay", "Look: Clay", lambda: w.set_look("clay"), "", "View", 2),
        Command("view.theme", "Choose Theme…", w.choose_theme, "Ctrl+K Ctrl+T", "View", 3),
        Command("view.theme_toggle", "Toggle Light/Dark Theme", w.toggle_theme, "", "View", 3),
        Command("build.run", "Build", w.workbench.build, "F5", "Build", 0, enabled=has_tab, tip="Build (F5)"),
        live,
        Command("build.cancel", "Cancel Build", w.workbench.cancel_build, "", "Build", 0),
        Command("build.seed_random", "Randomise Seed", w.random_seed, "Ctrl+Shift+R", "Build", 1, tip="Random seed"),
        Command("build.seed_next", "Seed +1", w.next_seed, "Alt+Right", "Build", 1, tip="Next seed"),
        Command("build.seed_prev", "Seed −1", w.previous_seed, "Alt+Left", "Build", 1),
        Command("build.variations", "Explore Seed Variations", w.explore_variations, "Ctrl+Shift+V", "Build", 2),
        Command("render.start", "Render", w.start_render, "F9", "Render", 0, tip="Render the current view (F9)"),
        Command("render.stop", "Stop Render", w.render_view.stop, "", "Render", 0),
        Command("render.save", "Save Render…", w.render_view.save_dialog, "", "Render", 1),
        Command("help.about", "About Structura", w.about, "", "Help", 0),
    ]


def _inserter(w: MainWindow, text: str) -> Callable[[], None]:
    return lambda: w.docs.insert_text(text)


def _snippets(w: MainWindow, has_tab: Predicate) -> list[Command]:
    return [
        Command(f"insert.{i}", s.title, _inserter(w, s.text), menu="Insert", submenu=s.group, enabled=has_tab)
        for i, s in enumerate(snippets())
    ]


def _exporter(w: MainWindow, name: str) -> Callable[[], None]:
    return lambda: w.exports.start(name)


def _exports(w: MainWindow, has_tab: Predicate) -> list[Command]:
    shortcuts = {"template": "F6"}  # F6 = template export, as in 1.5
    return [
        Command(f"export.{e.name}", f"{e.title}…", _exporter(w, e.name), shortcuts.get(e.name, ""), "Export",
                1 if e.name in ("template", "obj-legacy") else 0, enabled=has_tab)
        for e in w.exports.exporters()
    ]  # fmt: skip


def register_builtin(registry: CommandRegistry, w: MainWindow) -> None:
    def has_tab() -> bool:
        return w.tabs.current() is not None

    for group in (_file_edit, _view_build_render, _exports, _snippets):
        for command in group(w, has_tab):
            registry.register(command)
