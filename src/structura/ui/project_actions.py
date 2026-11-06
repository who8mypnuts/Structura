"""Project files in the window (docs/07 §8): open a .structura file into a tab, save the current tab as a
project (script linked when it is already saved as an .es file, embedded otherwise), and keep a thumbnail."""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QObject, Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox

from ..core.animation.timeline import Timeline
from ..core.project import model
from ..core.project.model import SUFFIX, Project
from .documents import EditorTab

if TYPE_CHECKING:
    from .app_window import MainWindow

PROJECT_FILTER = f"Structura project (*{SUFFIX})"
THUMBNAIL = 256


class ProjectActions(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window

    def open(self, path: Path) -> EditorTab | None:
        try:
            project = model.load(path)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self.w, "Cannot open project", f"{path.name}: {exc}")
            return None
        if project.linked:
            tab = self.w.tabs.open_file(path.parent / project.linked)
        else:
            tab = self.w.tabs.new_document(project.text)
        self.apply(tab, project, path)
        self.w.docs.recent.add(path)
        return tab

    def apply(self, tab: EditorTab, project: Project, path: Path) -> None:
        tab.project_path = path
        tab.seed, tab.params, tab.render_overrides = project.seed, dict(project.params), dict(project.render)
        tab.initial_camera = project.camera
        tab.timeline, tab.frame = project.timeline or Timeline(), (project.timeline or Timeline()).start
        tab.retitle()
        self.w.on_tab_changed(tab)

    def snapshot(self, tab: EditorTab, path: Path) -> Project:
        linked = None
        if tab.path is not None:
            linked = Path(os.path.relpath(tab.path, path.parent)).as_posix()
        return Project(
            text=tab.text(), linked=linked, seed=tab.seed, params=dict(tab.params),
            camera=self.w.viewport.camera() if tab.outcome is not None else tab.initial_camera,
            render=dict(tab.render_overrides), thumbnail_png_b64=self._thumbnail(),
            timeline=tab.timeline if tab.timeline != Timeline() else None,
        )  # fmt: skip

    def save(self, tab: EditorTab, path: Path | None = None) -> bool:
        target = path or tab.project_path
        if target is None:
            return self.save_as(tab)
        if tab.path is not None:
            tab.save()  # a linked script: its own file first
        model.save(target, self.snapshot(tab, target), tab.dialect)
        tab.project_path = target
        tab.editor.document().setModified(False)
        tab.retitle()
        self.w.show_message(f"Saved project {target.name}")
        return True

    def save_as(self, tab: EditorTab | None = None) -> bool:
        tab = tab or self.w.tabs.current()
        if tab is None:
            return False
        suggestion = tab.project_path or (tab.path.with_suffix(SUFFIX) if tab.path else Path("untitled" + SUFFIX))
        name, _ = QFileDialog.getSaveFileName(self.w, "Save project", str(suggestion), PROJECT_FILTER)
        return bool(name) and self.save(tab, Path(name).with_suffix(SUFFIX))

    def _thumbnail(self) -> str:
        image = self.w.viewport.grab().toImage()
        if image.isNull() or image.width() == 0:
            return ""
        scaled = image.scaled(THUMBNAIL, THUMBNAIL, Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)  # fmt: skip
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        scaled.save(buffer, "PNG")  # type: ignore[call-overload]  # PySide wants str; its stubs say bytes
        return base64.b64encode(bytes(data.data())).decode("ascii")
