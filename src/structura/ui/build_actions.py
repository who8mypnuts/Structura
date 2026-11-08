"""Build and viewport commands of the main window: live build, seeds, variations, looks and colour modes."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QObject, Slot

from .i18n import tr
from .viewport.overlay import Overlays

if TYPE_CHECKING:
    from .app_window import MainWindow


OVERLAYS = {"grid": False, "axes": True, "bounds": False, "hud": True}  # viewport overlay → default


class BuildActions(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window

    def toggle_live(self) -> None:
        self.w.workbench.live = not self.w.workbench.live
        self.w.show_message("Live build " + ("on" if self.w.workbench.live else "off"))

    def random_seed(self) -> None:
        self.w.header.set_seed(self.w.workbench.random_seed())

    def next_seed(self) -> None:
        self.w.header.set_seed(self.w.workbench.next_seed())

    def previous_seed(self) -> None:
        tab = self.w.tabs.current()
        seed = max(0, (tab.seed if tab else 0) - 1)
        self.w.header.set_seed(seed)
        self.w.workbench.set_seed(seed)

    def explore_variations(self) -> None:
        tab = self.w.tabs.current()
        if tab is None or tab.analysis is None or tab.analysis.program is None:
            self.w.show_message("The script must compile before exploring variations.")
            return
        self.w.panels.show("Variations")
        parameters = list(tab.analysis.parameters)
        if self.w.variations.mode.currentData() == "params" and parameters:
            base = {p.name: tab.params.get(p.name, p.default) for p in parameters}
            self.w.variations.explore_params(tab.text(), tab.seed, parameters, base)
        else:
            self.w.variations.explore(tab.analysis.program)

    @Slot(object)
    def adopt_params(self, params: object) -> None:
        """A parameter variation was chosen: its slider values become the tab's."""
        if isinstance(params, dict):
            self.w.workbench.set_parameters({str(k): float(v) for k, v in params.items()})

    @Slot(int)
    def adopt_seed(self, seed: int) -> None:
        self.w.header.set_seed(seed)
        self.w.workbench.set_seed(seed)

    def set_look(self, look: str) -> None:
        self.w.viewport.set_options(replace(self.w.viewport.options, look=look))

    def set_color_by(self, mode: str) -> None:
        """Colour the viewport by how the structure was made (renders and exports keep the authored colours)."""
        self.w.workbench.set_color_by(mode)
        self.w.show_message(tr("Viewport colours: {mode}").format(mode=tr(mode, "Commands")))

    def toggle_xray(self) -> None:
        view = self.w.workbench.view
        self.w.workbench.set_view(replace(view, xray=not view.xray))

    def isolate(self, rows: object) -> None:
        """Show only these SceneIR rows in the viewport (None: everything again)."""
        self.w.workbench.set_view(
            replace(self.w.workbench.view, isolate=rows if isinstance(rows, np.ndarray) else None)
        )

    # -- overlays ----------------------------------------------------------------------------------------------
    def overlay_on(self, name: str) -> bool:
        return bool(self.w.settings.value(f"viewport/{name}", OVERLAYS[name]))

    def toggle_overlay(self, name: str) -> None:
        self.w.settings.set_value(f"viewport/{name}", not self.overlay_on(name))
        self.apply_overlays()

    def apply_overlays(self) -> None:
        overlays = Overlays(self.overlay_on("axes"), self.overlay_on("bounds"), self.overlay_on("hud"))
        self.w.viewport.set_overlays(overlays, grid=self.overlay_on("grid"))
