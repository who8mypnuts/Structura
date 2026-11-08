"""File ▸ Save as Legacy .es… (docs/14 §4.1): a copy for Structure Synth 1.5 (core.lang.to_legacy), with a v2
camera block written back as 1.5 'set' lines. The copy is written on the io lane; what was lost goes to the
Console."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Slot

from ..core.lang.source import detect_dialect
from ..core.lang.to_legacy import legacy_copy
from ..core.lang.v2.front import front
from ..core.scene.camera_script import with_camera
from ..render.declarations import declared_camera
from ..services.jobs import FunctionJob, JobContext, Lane
from .i18n import tr
from .save_paths import SavePaths, stem_for, with_extension

if TYPE_CHECKING:
    from .app_window import MainWindow

FILTERS = ["Structure Synth 1.5 script (*.es)"]


def legacy_text(text: str, seed: int, fallback_camera: object) -> tuple[str, tuple[str, ...]]:
    copy = legacy_copy(text, seed)
    if detect_dialect(text) != 2:
        return copy.text, copy.notes
    camera = declared_camera(front(text).declarations, fallback_camera)  # type: ignore[arg-type]
    if camera is None:
        return copy.text, copy.notes
    return with_camera(copy.text, camera, False), (*copy.notes, "the camera block became 'set' lines")


class LegacySave(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        self.notes: dict[Path, tuple[str, ...]] = {}

    def save(self) -> None:
        tab = self.w.tabs.current()
        if tab is None:
            return
        paths = SavePaths(self.w.settings)
        suggestion = paths.suggest("script", stem_for(tab.path, "untitled") + "-1.5.es", tab.path)
        answer = paths.ask(self.w, "script", tr("Save as Legacy .es"), suggestion, FILTERS)
        if answer is None:
            return
        target = with_extension(answer[0], (".es",))
        text, self.notes[target] = legacy_text(tab.text(), tab.seed, self.w.viewport.camera())

        def run(ctx: JobContext) -> Path:
            target.write_text(text, encoding="utf-8")
            return target

        self.w.runner.submit(FunctionJob(f"save {target.name}", Lane.IO, run)).finished.connect(self._saved)

    @Slot(object)
    def _saved(self, path: object) -> None:
        if not isinstance(path, Path):
            return
        for note in self.notes.pop(path, ()):
            self.w.console.append_record(f"Legacy copy: {note}", logging.WARNING)
        self.w.notify_file(tr("Saved a Structure Synth 1.5 copy"), path)
