"""The Lights panel's actions: v2 light blocks added (placed around the structure), edited, removed and found in
the current script, and lighting rigs applied (v1 scripts are converted to v2 first, after asking)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QObject, Slot

from ..core.lang.v2.block_check import known_keys
from ..core.lang.v2.block_form import block_specs, block_text, entries_of
from ..core.scene.light_rigs import apply_rig, rigs
from ..core.scene.light_script import free_name, light_text
from ..core.scene.script_blocks import block_names, block_span, put_block, remove_block
from .i18n import tr

if TYPE_CHECKING:
    from .app_window import MainWindow
    from .documents import EditorTab
    from .workbench import PreviewReady


class LightActions(QObject):
    """The Lights panel's actions: add, edit, remove and find light blocks, and apply lighting rigs."""

    def __init__(self, window: MainWindow) -> None:
        """Connects the Lights panel to the current script.

        Args:
            window: The main window.
        """
        super().__init__(window)
        self.w = window
        panel = window.lights
        panel.add_requested.connect(self.add)
        panel.remove_requested.connect(self.remove)
        panel.go_to_requested.connect(self.go_to)
        panel.edit_requested.connect(self.edit)
        panel.rig_requested.connect(self.apply_rig)
        window.workbench.scene_ready.connect(self._scene_ready)

    @Slot(object, object, object, bool)
    def _scene_ready(self, tab: EditorTab, ready: PreviewReady, *_: object) -> None:
        if tab is self.w.tabs.current():
            self.w.lights.show_lights(ready.outcome.scene.declarations)

    def _v2_target(self) -> tuple[EditorTab, tuple[np.ndarray, np.ndarray]] | None:
        """The current tab (converted to v2 if the user agrees) and its structure's bounds; None: explained."""
        tab, bounds = self.w.tabs.current(), self.w.viewport.bounds()
        if tab is None or bounds is None:
            self.w.show_message(tr("Build the script first (F5)."))
            return None
        if not self.w.editor_actions.ensure_v2(tr("Add Light"), tr("Lights are")):
            return None
        return tab, bounds

    @Slot(str)
    def apply_rig(self, name: str) -> None:
        """Lights panel ▸ Lighting Rig: writes the rig's lights and environment, replacing an earlier rig's.

        The Render view's look follows the rig's, when it names one. Undo takes the rig back.

        Args:
            name: The rig's name (light_rigs.toml).
        """
        target, rig = self._v2_target(), rigs().get(name)
        if target is None or rig is None:
            return
        tab, bounds = target
        self.w.docs.replace_text(tab, apply_rig(tab.text(), rig, *bounds))
        if rig.look:
            self.w.render_view.controls.look.setCurrentText(rig.look)
        self.w.show_message(tr("Lighting rig '{name}' applied (Undo reverts it)").format(name=tr(name)))

    @Slot(str)
    def add(self, kind: str) -> None:
        """Adds a light of a kind, placed around the structure (v1 scripts are converted to v2 first).

        Args:
            kind: A light type ('sun', 'point', 'sphere', 'spot', 'rect').
        """
        target = self._v2_target()
        if target is None:
            return
        tab, bounds = target
        name = free_name(kind, block_names(tab.text(), "light"))
        self.w.docs.replace_text(tab, put_block(tab.text(), "light", name, light_text(kind, name, *bounds)))
        self.w.show_message(tr("Light '{name}' added to the script").format(name=name))

    @Slot(str)
    def remove(self, name: str) -> None:
        """Removes a light block from the current script.

        Args:
            name: The light's name.
        """
        tab = self.w.tabs.current()
        if tab is not None:
            self.w.docs.replace_text(tab, remove_block(tab.text(), "light", name))

    @Slot(str, dict)
    def edit(self, name: str, edited: dict[str, object]) -> None:
        """Rewrites a light block with the values of the Lights panel's form.

        Args:
            name: The light's name.
            edited: The form's values (type included); values that do not fit their key are dropped.
        """
        tab = self.w.tabs.current()
        if tab is None or block_span(tab.text(), "light", name) is None:
            return
        kind = str(edited.get("type", "sun"))
        entries = {"type": kind, **entries_of(block_specs("light", kind), edited, known_keys("light"))}
        self.w.docs.replace_text(tab, put_block(tab.text(), "light", name, block_text("light", name, entries)))

    @Slot(str)
    def go_to(self, name: str) -> None:
        """Moves the editor's cursor to a light block.

        Args:
            name: The light's name (nothing happens if the script has no such block).
        """
        tab = self.w.tabs.current()
        span = block_span(tab.text(), "light", name) if tab is not None else None
        if tab is not None and span is not None:
            tab.editor.go_to(span[0])
