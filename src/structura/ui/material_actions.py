"""The Materials panel's actions: swatch renders on the compute lane, and material blocks written into the script
(v1 scripts are converted to v2 first, after asking). The Lights panel's are in light_actions.py."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QObject, Slot

from ..compute.cpu import CpuBackend
from ..core.build.api import build_scene
from ..core.lang.api import compile_script
from ..core.scene.material import Material
from ..core.scene.material_script import material_text, with_material
from ..render.api import render
from ..render.output import Display
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
    """Makes the job that renders a material's swatch (a sphere and a box, path traced on the CPU).

    Args:
        material: The material the swatch shows (on a sphere and a box).

    Returns:
        The job function; its result is the swatch as uint8 RGB.
    """

    def run(ctx: JobContext) -> np.ndarray:
        """Builds the swatch scene with the material and renders it."""
        text = "#version 2\n" + material_text(replace(material, name="swatch")) + "\n" + SWATCH_SCENE
        scene = build_scene(compile_script(text).program).scene
        settings = RenderSettings(width=SWATCH[0], height=SWATCH[1], samples=16, samples_per_pass=16,
                                  integrator="path", frame=True)  # fmt: skip
        return Display(view="agx").apply(render(scene, settings, CpuBackend()).image)

    return run


class MaterialActions(QObject):
    """The Materials panel's actions: live swatches and 'Write to Script' (v1 scripts are converted first)."""

    def __init__(self, window: MainWindow) -> None:
        """Connects the Materials panel to the swatch renders and the script.

        Args:
            window: The main window.
        """
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
        """Writes a material block into the current script (after offering to convert a v1 script to v2).

        Args:
            material: The material from the Materials panel.
            preset: The preset it started from, the block starts from ("" or an unknown name: the default material).
        """
        tab = self.w.tabs.current()
        if tab is None:
            return
        if not self.w.editor_actions.ensure_v2(tr("Write Material"), tr("Material blocks are")):
            return
        self.w.docs.replace_text(tab, with_material(tab.text(), material, preset))
        self.w.show_message(tr("Material '{name}' written to the script").format(name=material.name))
