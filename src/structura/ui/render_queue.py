"""The render queue (docs/14 §3, §5.4): renders that run one after another on the device lane while the user
keeps working, each saved to its own file (and, optionally, with a report) when it finishes."""

from __future__ import annotations

import itertools
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Slot

from ..render.metadata import render_metadata
from ..render.output import save_image
from ..render.report.collect import ReportInputs, build_report
from ..services.jobs import ErrorInfo, FunctionJob, JobContext, Lane
from ..services.render import RenderRequest, RenderUpdate
from ..services.report_documents import write_report

if TYPE_CHECKING:
    from .app_window import MainWindow

PREFIX = "queue:"
_ids = itertools.count(1)


@dataclass
class QueueEntry:
    doc_id: str
    name: str
    request: RenderRequest
    path: Path  # the image to write
    script: str
    report: Path | None = None  # also write a report here
    state: str = "queued"  # queued | rendering | saving | done | failed | cancelled
    fraction: float = 0.0
    seconds: float = 0.0
    message: str = ""


def report_path(image: Path, suffix: str | None) -> Path | None:
    return image.with_name(f"{image.stem}-report{suffix}") if suffix else None


class RenderQueue(QObject):
    changed = Signal(object)  # QueueEntry

    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        self.entries: list[QueueEntry] = []
        self._pending_save: dict[QObject, QueueEntry] = {}
        renders = window.renders
        renders.progress.connect(self._progress)
        renders.finished.connect(self._finished)
        renders.failed.connect(self._failed)
        renders.cancelled.connect(self._cancelled)

    def add(self, name: str, request: RenderRequest, path: Path, script: str, report: Path | None) -> QueueEntry:
        doc_id = f"{PREFIX}{next(_ids)}"
        entry = QueueEntry(doc_id, name, replace(request, doc_id=doc_id), path, script, report)
        self.entries.append(entry)
        self.w.renders.request(entry.request)  # the device lane runs renders one at a time, in order
        self.changed.emit(entry)
        return entry

    def entry(self, doc_id: str) -> QueueEntry | None:
        return next((e for e in self.entries if e.doc_id == doc_id), None)

    def cancel(self, entry: QueueEntry) -> None:
        if entry.state in ("queued", "rendering"):
            self.w.renders.cancel(entry.doc_id)

    def remove(self, entry: QueueEntry) -> None:
        self.cancel(entry)
        self.entries.remove(entry)
        self.changed.emit(None)

    def clear_finished(self) -> None:
        self.entries = [e for e in self.entries if e.state not in ("done", "failed", "cancelled")]
        self.changed.emit(None)

    @Slot(str, object)
    def _progress(self, doc_id: str, update: object) -> None:
        entry = self.entry(doc_id)
        if entry is not None and isinstance(update, RenderUpdate):
            entry.state, entry.fraction, entry.seconds = "rendering", update.fraction, update.progress.seconds
            self.changed.emit(entry)

    @Slot(str, object)
    def _finished(self, doc_id: str, update: object) -> None:
        entry = self.entry(doc_id)
        if entry is None or not isinstance(update, RenderUpdate):
            return
        entry.state, entry.fraction = "saving", 1.0
        self.changed.emit(entry)
        handle = self.w.runner.submit(FunctionJob(f"save {entry.path.name}", Lane.IO, _save_job(entry, update)))
        handle.finished.connect(self._saved)
        handle.failed.connect(self._save_failed)
        self._pending_save[handle] = entry

    @Slot(object)
    def _saved(self, path: object) -> None:
        entry = self._pending_save.pop(self.sender(), None)
        if entry is not None:
            entry.state = "done"
            self.changed.emit(entry)
            self.w.notify_file(f"Queued render saved: {entry.path.name}", entry.path)

    @Slot(object)
    def _save_failed(self, info: object) -> None:
        entry = self._pending_save.pop(self.sender(), None)
        if entry is not None:
            entry.state, entry.message = "failed", info.message if isinstance(info, ErrorInfo) else str(info)
            self.changed.emit(entry)

    @Slot(str, object)
    def _failed(self, doc_id: str, info: object) -> None:
        entry = self.entry(doc_id)
        if entry is not None:
            entry.state, entry.message = "failed", info.message if isinstance(info, ErrorInfo) else str(info)
            self.changed.emit(entry)

    @Slot(str)
    def _cancelled(self, doc_id: str) -> None:
        entry = self.entry(doc_id)
        if entry is not None:
            entry.state = "cancelled"
            self.changed.emit(entry)


def _save_job(entry: QueueEntry, update: RenderUpdate) -> Callable[[JobContext], Path]:
    def run(ctx: JobContext) -> Path:
        request, details = entry.request, update.details
        image = update.denoised if update.denoised is not None else update.progress.image
        camera = details.camera if details is not None else request.camera
        assert camera is not None
        meta = render_metadata(request.settings, camera, entry.script)
        layers = update.progress.aovs.layers() if update.progress.aovs is not None else None
        exposure, view = request.display or (0.0, request.settings.view_transform)
        entry.path.parent.mkdir(parents=True, exist_ok=True)
        save_image(image, entry.path, exposure, view, meta, layers)
        if entry.report is not None and details is not None:
            inputs = ReportInputs(request.scene, update.progress, details, update.device, update.passes, image,
                                  update.denoiser, exposure, view, entry.script, outputs=(entry.path,))  # fmt: skip
            write_report(build_report(inputs), entry.report)
        return entry.path

    return run
