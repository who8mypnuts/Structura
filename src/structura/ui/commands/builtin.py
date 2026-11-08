"""The built-in commands (docs/14 §4.1–4.2). Handlers call into the main window; nothing else builds QActions."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from ...core.lang.catalog import snippets
from ...core.scene.color_by import MODES
from ..dock_layout import PANELS
from ..editor.options import LABELS, TOGGLES
from ..workspaces import WORKSPACES
from .registry import Command, CommandRegistry

if TYPE_CHECKING:
    from ..app_window import MainWindow

Predicate = Callable[[], bool]


def _file(w: MainWindow, has_tab: Predicate) -> list[Command]:
    d = w.docs
    return [
        Command("file.new", "New Script", d.new_script, "Ctrl+N", "File", 0),
        Command("file.open", "Open…", d.open_dialog, "Ctrl+O", "File", 0),
        Command("file.open_render", "Open from Render…", w.projects.open_render_dialog, "", "File", 0,
                tip="Reopen the script, seed, parameters, camera and settings stored in a PNG or EXR render"),
        Command("file.quick_open", "Quick Open…", w.quick_open.open, "Ctrl+P", "File", 0,
                tip="Open tabs, recent files and examples · @ rules · : line"),
        Command("file.save", "Save", d.save, "Ctrl+S", "File", 1, enabled=has_tab),
        Command("file.save_as", "Save As…", d.save_as, "Ctrl+Shift+S", "File", 1, enabled=has_tab),
        Command("file.save_legacy", "Save as Legacy .es…", d.legacy.save, "", "File", 1, enabled=has_tab,
                tip="A copy Structure Synth 1.5 opens (v2 features flattened or dropped; notes in the Console)"),
        Command("file.revert", "Revert File", d.revert, "", "File", 1, enabled=has_tab,
                tip="Reload from disk, discarding unsaved edits"),
        Command("file.save_project", "Save Project As…", w.projects.save_as, "", "File", 1, enabled=has_tab,
                tip="Save the script with its seed, parameters, camera and render settings (.structura)"),
        Command("file.export_as", "Export As…", w.exports.start, "Ctrl+E", "File", 1,
                enabled=has_tab, tip="Export the structure: choose the folder, file name and format"),
        Command("file.close", "Close Tab", d.close_tab, "Ctrl+W", "File", 1, enabled=has_tab),
        Command("file.preferences", "Preferences…", w.dialogs.preferences, "Ctrl+,", "File", 8),
        Command("file.keymap", "Keyboard Shortcuts…", w.dialogs.edit_keymap, "Ctrl+K, Ctrl+S", "File", 8),
        Command("file.quit", "Quit", w.close, "Ctrl+Q", "File", 9),
    ]  # fmt: skip


def _edit(w: MainWindow, has_tab: Predicate) -> list[Command]:
    d = w.docs
    return [
        Command("edit.find", "Find…", lambda: d.open_find(False), "Ctrl+F", "Edit", 0, enabled=has_tab),
        Command("edit.find_in_files", "Find in Files…", lambda: w.search.show(), "Ctrl+Shift+F", "Edit", 0,  # noqa: PLW0108 - created after the commands
                tip="Search the open scripts and the current folder"),
        Command("edit.replace", "Replace…", lambda: d.open_find(True), "Ctrl+H", "Edit", 0, enabled=has_tab),
        Command("edit.comment", "Toggle Line Comment", d.toggle_comment, "", "Edit", 1, enabled=has_tab),
        Command("edit.pick_color", "Pick Colour…", d.pick_color_at_cursor, "Ctrl+Shift+C", "Insert", 9,
                enabled=has_tab, tip="Edit the colour at the cursor, or insert one (also: right-click a colour)"),
        Command("edit.definition", "Go to Definition", d.definition_under_cursor, "F12", "Edit", 1, enabled=has_tab),
        Command("edit.rename", "Rename Rule…", d.rename_rule, "F2", "Edit", 1, enabled=has_tab),
        Command("edit.references", "Find References", d.find_references, "Shift+F12", "Edit", 1, enabled=has_tab),
        Command("edit.format", "Format Document", d.format_document, "Shift+Alt+F", "Edit", 1, enabled=has_tab),
        Command("edit.zoom_in", "Zoom In", lambda: d.zoom(1), "Ctrl+=", "Edit", 2, enabled=has_tab),
        Command("edit.zoom_out", "Zoom Out", lambda: d.zoom(-1), "Ctrl+-", "Edit", 2, enabled=has_tab),
    ]  # fmt: skip


def _canceller(w: MainWindow) -> Callable[[], None]:
    def cancel() -> None:
        w.workbench.cancel_build()
        w.scripts.cancel()

    return cancel


def _view_help(w: MainWindow, has_tab: Predicate) -> list[Command]:
    return [
        Command("view.palette", "Command Palette", w.command_palette.open, "Ctrl+Shift+P", "View", 0),
        Command("view.frame_all", "Frame All", w.viewport.frame_all, "", "View", 1, tip="Frame the structure"),
        Command("view.frame_selection", "Frame Selection", w.viewport.frame_selection, "", "View", 1,
                tip="Frame the object you clicked (Shift+F in the viewport)"),
        Command("view.camera_to_script", "Copy Camera to Script", w.cameras.copy_to_script, "", "View", 1,
                enabled=has_tab, tip="Write the viewport camera into the script (v1 'set' lines or a v2 camera block)"),
        *(Command(f"view.camera_{name}", title, _viewer(w, name), "", "View", 1, submenu="Standard Views")
          for name, title in VIEW_TITLES.items()),
        Command("view.fullscreen", "Full Screen", w.dialogs.toggle_fullscreen, "F11", "View", 1),
        Command("view.look_studio", "Look: Studio", lambda: w.build_actions.set_look("studio"), "", "View", 2),
        Command("view.look_legacy", "Look: Legacy", lambda: w.build_actions.set_look("legacy"), "", "View", 2),
        Command("view.look_clay", "Look: Clay", lambda: w.build_actions.set_look("clay"), "", "View", 2),
        Command("view.xray", "X-Ray", w.build_actions.toggle_xray, "", "View", 2, checkable=True,
                checked=lambda: w.workbench.view.xray, tip="See through the structure (the viewport only)"),
        Command("view.rendered", "Rendered View", lambda: w.viewport.set_rendered(not w.viewport.rendered),
                "Ctrl+Alt+V", "View", 2, checkable=True, checked=lambda: w.viewport.rendered,
                tip="Path-trace the viewport with the script's render settings (as in Blender's rendered view)"),
        Command("view.show_all", "Show All", lambda: w.build_actions.isolate(None), "", "View", 2,
                tip="Show the objects hidden by Isolate Selection (Inspector)"),
        Command("view.look_technical", "Look: Technical", lambda: w.build_actions.set_look("technical"), "", "View", 2,
                tip="Flat colours with dark edges"),
        Command("view.theme", "Choose Theme…", w.dialogs.choose_theme, "Ctrl+K, Ctrl+T", "View", 3),
        Command("view.theme_edit", "Edit Theme…", w.dialogs.edit_theme, "", "View", 3,
                tip="Colours, contrast and syntax styles of the current theme"),
        Command("view.theme_toggle", "Toggle Light/Dark Theme", w.dialogs.toggle_theme, "", "View", 3),
        Command("help.reference", "Language Reference", w.help.reference, "F1", "Help", 0,
                tip="The EisenScript reference at the symbol under the cursor"),
        Command("help.guide", "User Guide", w.help.guide, "", "Help", 0),
        Command("help.quick_start", "Quick Start", lambda: w.help.guide("getting-started.md"), "", "Help", 0),
        Command("help.examples", "Examples", lambda: w.panels.show("Examples"), "", "Help", 0),
        Command("help.whats_new", "What's New", lambda: w.help.guide("changelog.md"), "", "Help", 1),
        Command("help.system_report", "System Report…", w.help.system_report, "", "Help", 1,
                tip="What Structura sees of this computer (for bug reports)"),
        Command("help.about", "About Structura", w.dialogs.about, "", "Help", 1),
    ]  # fmt: skip


COLOR_TITLES = {"authored": "Authored Colours", "generation": "Generation", "call site": "Call Site", "tag": "Tag",
                "kind": "Primitive Kind", "random": "Random"}  # fmt: skip


def _color_by(w: MainWindow, mode: str) -> tuple[Callable[[], None], Callable[[], bool]]:
    return (lambda: w.build_actions.set_color_by(mode)), (lambda: w.workbench.color_by == mode)


OVERLAY_TITLES = {"grid": "Ground Grid", "axes": "Axis Gizmo", "bounds": "Bounding Box", "hud": "Object Counts"}


def _overlay(w: MainWindow, name: str) -> tuple[Callable[[], None], Callable[[], bool]]:
    return (lambda: w.build_actions.toggle_overlay(name)), (lambda: w.build_actions.overlay_on(name))


def _colors(w: MainWindow, has_tab: Predicate) -> list[Command]:
    commands = []
    for mode in MODES:
        handler, current = _color_by(w, mode)
        commands.append(Command(f"view.color_{mode.replace(' ', '_')}", COLOR_TITLES[mode], handler, "", "View", 2,
                                checkable=True, checked=current, submenu="Colour By"))  # fmt: skip
    for name, title in OVERLAY_TITLES.items():
        handler, on = _overlay(w, name)
        commands.append(Command(f"view.overlay_{name}", title, handler, "", "View", 2, checkable=True, checked=on,
                                submenu="Overlays"))  # fmt: skip
    return commands


VIEW_TITLES = {"front": "Front", "back": "Back", "right": "Right", "left": "Left", "top": "Top", "bottom": "Bottom",
               "iso": "Isometric"}  # fmt: skip


def _viewer(w: MainWindow, name: str) -> Callable[[], None]:
    return lambda: w.cameras.standard_view(name)


def _build_render(w: MainWindow, has_tab: Predicate) -> list[Command]:
    b = w.build_actions
    live = Command(
        "build.live", "Live Build", b.toggle_live, menu="Build", checkable=True,
        checked=lambda: w.workbench.live, tip="Rebuild while typing",
    )  # fmt: skip
    return [
        Command("build.run", "Build", w.workbench.build, "F5", "Build", 0, enabled=has_tab, tip="Build (F5)"),
        live,
        Command("build.cancel", "Cancel Build", _canceller(w), "", "Build", 0, tip="Stop the build or script"),
        Command("build.run_js", "Run JavaScript", w.scripts.run, "F7", "Build", 0, enabled=w.scripts.can_run,
                tip="Run this '#javascript' script (Builder API); files go next to the script"),
        Command("build.run_python", "Run Python Script…", w.scripts.run_python, "", "Build", 0,
                tip="A script that uses the Python API (import structura as st); output in the Console"),
        Command("build.seed_random", "Randomise Seed", b.random_seed, "Ctrl+Shift+R", "Build", 1, tip="Random seed"),
        Command("build.seed_next", "Seed +1", b.next_seed, "Alt+Right", "Build", 1, tip="Next seed"),
        Command("build.seed_prev", "Seed −1", b.previous_seed, "Alt+Left", "Build", 1),
        Command("build.variations", "Explore Seed Variations", b.explore_variations, "Ctrl+Shift+V", "Build", 2),
        Command("build.limits", "Build Limits…", b.edit_limits, "", "Build", 3,
                tip="Object, time and memory limits for every build"),
        Command("build.ancestry", "Show Ancestry", b.ancestry_of_selection, "", "Build", 3, enabled=has_tab,
                tip="How the picked object was made: its chain of rule calls"),
        Command("build.snapshot", "Take Snapshot", w.history_actions.take, "Ctrl+Alt+H", "Build", 2, enabled=has_tab,
                tip="Keep the script, seed, parameters and camera in the History panel"),
        *_render(w, has_tab),
        Command("timeline.play", "Play / Pause Timeline", _play(w), "Ctrl+Alt+Space", "View", 5, enabled=has_tab),
        Command("timeline.next", "Next Frame", lambda: w.timeline.step(1), "Alt+.", "View", 5, enabled=has_tab),
        Command("timeline.previous", "Previous Frame", lambda: w.timeline.step(-1), "Alt+,", "View", 5,
                enabled=has_tab),
        Command("timeline.key_camera", "Key Camera", w.timeline.key_camera, "", "View", 5, enabled=has_tab,
                tip="Key the viewport camera at the current frame"),
    ]  # fmt: skip


def _render(w: MainWindow, has_tab: Predicate) -> list[Command]:
    return [
        Command("render.start", "Render", w.render_actions.start_render, "F9", "Render", 0,
                tip="Render the current view (F9)"),
        Command("render.final", "Final Render…", w.render_actions.final_render, "Shift+F9", "Render", 0,
                tip="Choose the quality, where the image goes and the report beside it; saved when finished"),
        Command("render.stop", "Stop Render", w.render_view.stop, "", "Render", 0),
        Command("render.legacy", "Render (Legacy Look)", w.render_actions.render_legacy, "", "Render", 0,
                tip="The classic integrator: Structure Synth 1.5's raytracer look"),
        Command("render.region", "Render Region", w.render_actions.render_region, "", "Render", 1,
                tip="Drag over the rendered image to render that part again (or Shift+drag any time)"),
        Command("render.denoise", "Denoise", w.render_actions.denoise, "", "Render", 1,
                tip="Denoise the finished render (Open Image Denoise, else À-Trous)"),
        Command("render.queue", "Add to Render Queue…", w.render_actions.queue_render, "Ctrl+Shift+F9", "Render", 0,
                enabled=has_tab, tip="Render the current view later, into a file, while you keep working"),
        Command("render.save", "Save Render…", w.render_actions.save_render, "Ctrl+Alt+S", "Render", 1,
                tip="Save the rendered image (PNG, EXR with AOVs, JPEG, …) and a report beside it"),
        Command("render.report", "Save Render Report…", w.render_actions.save_report, "", "Render", 1,
                tip="Everything about the render: scene, camera, settings, image statistics, performance"),
        Command("render.animation", "Render Animation…", w.animations.render, "", "Render", 2, enabled=has_tab,
                tip="Render the timeline's frames (and a video) with the precision engine"),
        Command("render.animation_stop", "Stop Animation", w.animations.cancel, "", "Render", 2),
    ]  # fmt: skip


def _play(w: MainWindow) -> Callable[[], None]:
    return lambda: w.timeline.play(not w.timeline.timer.isActive())


def _toggler(w: MainWindow, name: str) -> tuple[Callable[[], None], Callable[[], bool]]:
    return (lambda: w.editor_actions.toggle(name)), (lambda: bool(getattr(w.editor_actions.options(), name)))


STANDARD_EDITS = (
    ("undo", "Undo", "Ctrl+Z"), ("redo", "Redo", "Ctrl+Shift+Z"), ("cut", "Cut", "Ctrl+X"),
    ("copy", "Copy", "Ctrl+C"), ("paste", "Paste", "Ctrl+V"), ("selectAll", "Select All", "Ctrl+A"),
)  # fmt: skip


def _standard(w: MainWindow, name: str) -> Callable[[], None]:
    return lambda: w.editor_actions.standard(name)


def _editor(w: MainWindow, has_tab: Predicate) -> list[Command]:
    e = w.editor_actions
    commands = [
        *(Command(f"edit.{name.lower()}", title, _standard(w, name), "", "Edit", -1, enabled=has_tab,
                  tip=f"{title} ({shortcut})") for name, title, shortcut in STANDARD_EDITS),
        Command("edit.peek", "Peek Definition", e.peek, "Alt+F12", "Edit", 1, enabled=has_tab,
                tip="Show the rule's definition in place"),
        Command("edit.quick_fix", "Quick Fix…", e.quick_fix, "Ctrl+.", "Edit", 1, enabled=has_tab,
                tip="Fixes for the problem at the cursor"),
        Command("edit.refactor", "Refactor…", e.refactor, "Ctrl+Alt+R", "Edit", 1, enabled=has_tab,
                tip="Extract a rule, inline a rule, add or drop '1 *'"),
        Command("edit.block_comment", "Toggle Block Comment", e.block_comment, "Shift+Alt+A", "Edit", 1,
                enabled=has_tab),
        Command("edit.convert_v2", "Convert to EisenScript v2", e.convert_to_v2, "", "Edit", 2, enabled=has_tab,
                tip="Migrate a Structure Synth 1.5 script; it builds the same (notes in the console)"),
        Command("edit.fold", "Fold", e.fold, "Ctrl+Shift+[", "Edit", 3, enabled=has_tab, submenu="Folding"),
        Command("edit.unfold", "Unfold", e.unfold, "Ctrl+Shift+]", "Edit", 3, enabled=has_tab, submenu="Folding"),
        Command("edit.fold_all", "Fold All", e.fold_all, "Ctrl+K, Ctrl+0", "Edit", 3, enabled=has_tab,
                submenu="Folding"),
        Command("view.split", "Split Editor", e.split, "Ctrl+\\", "View", 4, enabled=has_tab,
                tip="A second view of the script beside the first"),
        Command("edit.unfold_all", "Unfold All", e.unfold_all, "Ctrl+K, Ctrl+J", "Edit", 3, enabled=has_tab,
                submenu="Folding"),
    ]  # fmt: skip
    for name in TOGGLES:
        handler, checked = _toggler(w, name)
        title = LABELS[name].split(" (")[0]
        shortcut = "Alt+Z" if name == "word_wrap" else ""
        commands.append(Command(f"view.{name}", title, handler, shortcut, "View", 4, checkable=True,
                                checked=checked, submenu="Editor"))  # fmt: skip
    return commands


def _workspace(w: MainWindow, name: str) -> tuple[Callable[[], None], Callable[[], bool]]:
    return (lambda: w.workspaces.switch(name)), (lambda: w.workspaces.current == name and not w.workspaces.presenting)


def _workspaces(w: MainWindow, has_tab: Predicate) -> list[Command]:
    commands = []
    for ws in WORKSPACES:
        handler, current = _workspace(w, ws.name)
        commands.append(Command(f"view.workspace_{ws.name.lower()}", ws.name, handler, ws.shortcut, "View", 7,
                                checkable=True, checked=current, submenu="Workspace"))  # fmt: skip
    reset = Command("view.reset_layout", "Reset Layout", w.workspaces.reset_layout, "", "View", 7, submenu="Workspace",
                    tip="Put every panel back where it started")  # fmt: skip
    present = Command("view.present", "Present", w.workspaces.present, "Ctrl+4", "View", 7, checkable=True,
                      checked=lambda: bool(w.workspaces.presenting), submenu="Workspace",
                      tip="Only the image, full screen (Esc returns)")  # fmt: skip
    return [*commands, present, reset]


def _panel_toggle(w: MainWindow, title: str) -> tuple[Callable[[], None], Callable[[], bool]]:
    return (lambda: w.panels.toggle(title)), (lambda: w.panels.visible(title))


def _panels(w: MainWindow, has_tab: Predicate) -> list[Command]:
    commands = []
    for panel in PANELS:
        handler, visible = _panel_toggle(w, panel.title)
        commands.append(Command(panel.command_id, panel.title, handler, panel.shortcut, "View", 6, checkable=True,
                                checked=visible, submenu="Panels"))  # fmt: skip
    return commands


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

    for group in (_file, _edit, _editor, _view_help, _colors, _panels, _workspaces, _build_render, _exports, _snippets):
        for command in group(w, has_tab):
            registry.register(command)
