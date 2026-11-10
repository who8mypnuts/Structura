"""The viewport's right-click menu: the view commands that matter while looking at a structure, taken from
the command registry (no second set of actions): framing, standard views, looks, overlays, the orbit lock,
the controls preset, Copy Camera to Script and the rendered view."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QPoint, Slot
from PySide6.QtWidgets import QMenu

from .i18n import tr

if TYPE_CHECKING:
    from .app_window import MainWindow

SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (  # (submenu title or "", command ids)
    ("", ("view.frame_all", "view.frame_selection", "view.camera_to_script")),
    ("Standard Views", tuple(f"view.camera_{n}" for n in ("front", "back", "right", "left", "top", "bottom", "iso"))),
    ("Look", ("view.look_studio", "view.look_legacy", "view.look_clay", "view.look_technical", "view.xray")),
    ("Overlays", tuple(f"view.overlay_{n}" for n in ("grid", "axes", "bounds", "hud", "focus"))),
    ("Orbit Lock", tuple(f"view.orbit_lock_{n}" for n in ("free", "horizontal", "vertical"))),
    ("Controls", tuple(f"view.controls_{n}" for n in ("structura", "legacy", "blender"))),
    ("", ("view.rendered", "view.show_all")),
)


class ViewportMenu(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        window.viewport.menu_requested.connect(self.popup)

    def build(self) -> QMenu:
        menu = QMenu(self.w.viewport)
        self.w.registry.refresh()  # check marks and enablement as of now
        for index, (title, ids) in enumerate(SECTIONS):
            if index:
                menu.addSeparator()
            target = menu.addMenu(tr(title, "Menus")) if title else menu
            for command_id in ids:
                target.addAction(self.w.registry.action(command_id))
        return menu

    @Slot(QPoint)
    def popup(self, pos: QPoint) -> None:
        self.build().popup(self.w.viewport.mapToGlobal(pos))
