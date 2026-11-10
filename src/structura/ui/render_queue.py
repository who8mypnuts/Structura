"""The render queue (docs/14 §3, §5.4): renders that run one after another on the device lane while the user
keeps working, each saved to its own file (and, optionally, with a report) when it finishes. Exports are
listed too (they run on the io lane as soon as they are asked for), so every long job is in one place."""

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

PREFIX, EXPORT_PREFIX = "queue:", "export:"
_ids = itertools.count(1)


@dataclass
class QueueEntry:
    doc_id: str
    name: str
    request: RenderRequest | None  # None: an export
    path: Path  # the image (or export) to write
    script: str
    report: Path | None = None  # also write a report here
    state: str = "queued"  # queued | rendering | exporting | saving | done | failed | cancelled
    fraction: float = 0.0
    seconds: float = 0.0
    message: str = ""


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
        queued = replace(request, doc_id=doc_id)
        entry = QueueEntry(doc_id, name, queued, path, script, report)
        self.entries.append(entry)
        self.w.renders.request(queued)  # the device lane runs renders one at a time, in order
        self.changed.emit(entry)
        return entry

    def entry(self, doc_id: str) -> QueueEntry | None:
        return next((e for e in self.entries if e.doc_id == doc_id), None)

    def cancel(self, entry: QueueEntry) -> None:
        if entry.request is None and entry.state == "exporting":
            self.w.exports.service.cancel(str(entry.path))
        elif entry.state in ("queued", "rendering"):
            self.w.renders.cancel(entry.doc_id)

    # -- exports -------------------------------------------------------------------------------------------------
    def track_export(self, name: str, path: Path) -> QueueEntry:
        entry = QueueEntry(f"{EXPORT_PREFIX}{path}", name, None, path, "", state="exporting")
        self.entries.append(entry)
        self.changed.emit(entry)
        return entry

    def export_progress(self, path: Path, fraction: float) -> None:
        self._export_state(path, "exporting", fraction)

    def export_ended(self, path: Path, state: str, message: str = "") -> None:
        """'done', 'failed' or 'cancelled'."""
        self._export_state(path, state, 1.0 if state == "done" else None, message)

    def _export_state(self, path: Path, state: str, fraction: float | None, message: str = "") -> None:
        entry = self.entry(f"{EXPORT_PREFIX}{path}")
        if entry is not None and entry.state == "exporting":
            entry.state, entry.message = state, message
            entry.fraction = entry.fraction if fraction is None else fraction
            self.changed.emit(entry)

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
    """Makes the io-lane job that saves a finished queued render and its report.

    Args:
        entry: The queue entry (its request, image file and report file).
        update: The finished render.

    Returns:
        The job function; its result is the image file.
    """

    def run(ctx: JobContext) -> Path:
        """Writes the image (denoised when there is a denoised one) and the report beside it."""
        request, details = entry.request, update.details
        assert request is not None  # (a render entry)
        image = update.denoised if update.denoised is not None else update.progress.image
        camera = details.camera if details is not None else request.camera
        assert camera is not None
        display = request.display or request.settings.display
        meta = render_metadata(request.settings, camera, entry.script, display=display)
        layers = update.progress.aovs.layers() if update.progress.aovs is not None else None
        entry.path.parent.mkdir(parents=True, exist_ok=True)
        save_image(image, entry.path, display, meta, layers)
        if entry.report is not None and details is not None:
            inputs = ReportInputs(request.scene, update.progress, details, update.device, update.passes, image,
                                  update.denoiser, display, entry.script, outputs=(entry.path,))  # fmt: skip
            write_report(build_report(inputs), entry.report)
        return entry.path

    return run
