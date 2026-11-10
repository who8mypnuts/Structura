"""The Materials and Lights panels' actions: swatch renders on the compute lane, and material and light blocks
written into the script (v1 scripts are converted to v2 first, after asking)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QMessageBox

from ..compute.cpu import CpuBackend
from ..core.build.api import build_scene
from ..core.lang.api import compile_script
from ..core.lang.v2.block_check import known_keys
from ..core.lang.v2.block_form import block_specs, block_text, entries_of
from ..core.scene.light_rigs import apply_rig, rigs
from ..core.scene.light_script import free_name, light_text
from ..core.scene.material import Material
from ..core.scene.material_script import material_text, with_material
from ..core.scene.script_blocks import block_names, block_span, put_block, remove_block
from ..render.api import render
from ..render.output import to_display
from ..render.settings import RenderSettings
from ..services.jobs import FunctionJob, JobContext, Lane
from .i18n import tr

if TYPE_CHECKING:
    from .app_window import MainWindow
    from .documents import EditorTab
    from .workbench import PreviewReady

SWATCH = (176, 96)
SWATCH_SCENE = (
    "set background #3b4252\n{ x -0.7 color #c8c8c8 } sphere::swatch\n"
    "{ x 0.55 s 0.85 rx 25 ry 35 color #c8c8c8 } box::swatch\n"
)


def swatch_job(material: Material) -> Callable[[JobContext], np.ndarray]:
    def run(ctx: JobContext) -> np.ndarray:
        text = "#version 2\n" + material_text(replace(material, name="swatch")) + "\n" + SWATCH_SCENE
        scene = build_scene(compile_script(text).program).scene
        settings = RenderSettings(width=SWATCH[0], height=SWATCH[1], samples=16, samples_per_pass=16,
                                  integrator="path", frame=True)  # fmt: skip
        return to_display(render(scene, settings, CpuBackend()).image, 0.0, "agx")

    return run


class MaterialActions(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        panel = window.materials
        panel.preview_requested.connect(self.preview)
        panel.apply_requested.connect(self.apply)
        window.workbench.scene_ready.connect(self._scene_ready)

    @Slot(object, object, object, bool)
    def _scene_ready(self, tab: EditorTab, ready: PreviewReady, *_: object) -> None:
        if tab is self.w.tabs.current():
            self.w.materials.show_scene(ready.outcome.scene)

    @Slot(object)
    def preview(self, material: Material) -> None:
        handle = self.w.runner.submit(FunctionJob("material swatch", Lane.COMPUTE, swatch_job(material),
                                                  key="material-swatch"))  # fmt: skip
        handle.finished.connect(self._swatch)

    @Slot(object)
    def _swatch(self, rgb: object) -> None:
        if isinstance(rgb, np.ndarray):
            self.w.materials.show_swatch(rgb)

    @Slot(object, str)
    def apply(self, material: Material, preset: str) -> None:
        tab = self.w.tabs.current()
        if tab is None:
            return
        if tab.dialect != 2:
            question = tr("Material blocks are EisenScript v2. Convert this script to v2 first? It builds the same.")
            buttons = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            if QMessageBox.question(self.w, tr("Write Material"), question, buttons) != QMessageBox.StandardButton.Yes:
                return
            self.w.editor_actions.convert_to_v2()
        self.w.docs.replace_text(tab, with_material(tab.text(), material, preset))
        self.w.show_message(tr("Material '{name}' written to the script").format(name=material.name))


class LightActions(QObject):
    """Adds, removes and finds v2 light blocks in the current script."""

    def __init__(self, window: MainWindow) -> None:
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
        if tab.dialect != 2 and not self._convert():
            return None
        return tab, bounds

    @Slot(str)
    def apply_rig(self, name: str) -> None:
        """Lights panel ▸ Lighting Rig: the rig's lights and environment, replacing an earlier rig's."""
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
        target = self._v2_target()
        if target is None:
            return
        tab, bounds = target
        name = free_name(kind, block_names(tab.text(), "light"))
        self.w.docs.replace_text(tab, put_block(tab.text(), "light", name, light_text(kind, name, *bounds)))
        self.w.show_message(tr("Light '{name}' added to the script").format(name=name))

    def _convert(self) -> bool:
        question = tr("Lights are EisenScript v2 blocks. Convert this script to v2 first? It builds the same.")
        buttons = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        if QMessageBox.question(self.w, tr("Add Light"), question, buttons) != QMessageBox.StandardButton.Yes:
            return False
        self.w.editor_actions.convert_to_v2()
        return True

    @Slot(str)
    def remove(self, name: str) -> None:
        tab = self.w.tabs.current()
        if tab is not None:
            self.w.docs.replace_text(tab, remove_block(tab.text(), "light", name))

    @Slot(str, dict)
    def edit(self, name: str, edited: dict[str, object]) -> None:
        """The Lights panel's form: rewrite the light block with the edited values."""
        tab = self.w.tabs.current()
        if tab is None or block_span(tab.text(), "light", name) is None:
            return
        kind = str(edited.get("type", "sun"))
        entries = {"type": kind, **entries_of(block_specs("light", kind), edited, known_keys("light"))}
        self.w.docs.replace_text(tab, put_block(tab.text(), "light", name, block_text("light", name, entries)))

    @Slot(str)
    def go_to(self, name: str) -> None:
        tab = self.w.tabs.current()
        span = block_span(tab.text(), "light", name) if tab is not None else None
        if tab is not None and span is not None:
            tab.editor.go_to(span[0])
