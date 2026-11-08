"""The Camera panel's actions (docs/08 §7, docs/14 §3): follow the viewport, standard views, saved views and
Copy Camera to Script; and the History panel's snapshots (docs/14 §5.3)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QInputDialog

from ..core.scene.camera import Camera
from ..core.scene.camera_script import with_camera
from .i18n import tr
from .panels.history import Snapshot
from .workbench import script_camera

if TYPE_CHECKING:
    from .app_window import MainWindow
    from .documents import EditorTab


class CameraActions(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        panel = window.camera_panel
        window.viewport.camera_changed.connect(panel.show_camera)
        panel.camera_edited.connect(window.viewport.set_camera)
        panel.view_requested.connect(self.standard_view)
        panel.copy_to_script.connect(self.copy_to_script)
        panel.bookmark_requested.connect(self.save_view)
        panel.bookmark_chosen.connect(window.viewport.move_camera)
        panel.bookmark_deleted.connect(self.delete_view)
        panel.lock_toggled.connect(self.lock_to_script)
        window.tabs.current_tab_changed.connect(self._tab_changed)

    @Slot(object)
    def _tab_changed(self, tab: EditorTab | None) -> None:
        self.w.camera_panel.set_bookmarks(tab.bookmarks if tab is not None else {})
        self.w.camera_panel.set_locked(tab is not None and tab.camera_locked)

    @Slot(bool)
    def lock_to_script(self, locked: bool) -> None:
        """Camera ▸ Lock to Script: every build (and now) shows the script's camera."""
        tab = self.w.tabs.current()
        if tab is None:
            return
        tab.camera_locked = locked
        camera = script_camera(tab.outcome.scene) if locked and tab.outcome is not None else None
        if camera is not None:
            self.w.viewport.move_camera(camera)

    @Slot(str)
    def standard_view(self, name: str) -> None:
        if self.w.viewport.bounds() is None:
            self.w.show_message(tr("Build the script first (F5)."))
            return
        self.w.viewport.standard_view(name)

    @Slot()
    def copy_to_script(self) -> None:
        """Replace the script's camera ('set' lines in v1, the camera block in v2) with the viewport's."""
        tab = self.w.tabs.current()
        if tab is None:
            return
        text = with_camera(tab.text(), self.w.viewport.camera(), tab.dialect == 2)
        self.w.docs.replace_text(tab, text)
        self.w.show_message(tr("Camera written to the script"))

    @Slot()
    def save_view(self) -> None:
        tab = self.w.tabs.current()
        if tab is None:
            return
        name, ok = QInputDialog.getText(self.w, tr("Save View"), tr("Name"), text=f"View {len(tab.bookmarks) + 1}")
        if ok and name.strip():
            self.add_view(tab, name.strip(), self.w.viewport.camera())

    def add_view(self, tab: EditorTab, name: str, camera: Camera) -> None:
        tab.bookmarks[name] = camera  # kept with the tab; saved in projects (.structura)
        self.w.camera_panel.set_bookmarks(tab.bookmarks)

    @Slot(str)
    def delete_view(self, name: str) -> None:
        tab = self.w.tabs.current()
        if tab is not None and tab.bookmarks.pop(name, None) is not None:
            self.w.camera_panel.set_bookmarks(tab.bookmarks)


class HistoryActions(QObject):
    """Snapshots of the current tab (History panel): take one, restore one."""

    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        window.history.take_requested.connect(self.take)
        window.history.restore_requested.connect(self.restore)
        window.tabs.current_tab_changed.connect(self._tab_changed)

    @Slot(object)
    def _tab_changed(self, tab: EditorTab | None) -> None:
        self.w.history.show_snapshots(tab.snapshots if tab is not None else [])

    def take(self) -> None:
        tab = self.w.tabs.current()
        if tab is None:
            return
        image = self.w.viewport.grab().toImage()
        tab.snapshots.append(Snapshot(tab.text(), tab.seed, dict(tab.params), self.w.viewport.camera(), image))
        self.w.history.show_snapshots(tab.snapshots)
        self.w.panels.show("History")

    @Slot(object)
    def restore(self, snapshot: Snapshot) -> None:
        tab = self.w.tabs.current()
        if tab is None:
            return
        if tab.text() != snapshot.text:
            self.w.docs.replace_text(tab, snapshot.text)  # one undo step
        tab.params = dict(snapshot.params)
        self.w.header.set_seed(snapshot.seed)
        self.w.workbench.set_seed(snapshot.seed)
        self.w.workbench.build(tab)
        self.w.viewport.move_camera(snapshot.camera)
        self.w.show_message(tr("Restored the snapshot of {time}").format(time=snapshot.taken))
