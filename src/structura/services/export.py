"""ExportService: exports run as io-lane Jobs with progress and cancellation (docs/15 §1)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PySide6.QtCore import Signal, Slot

from ..core.scene.camera import Camera
from ..core.scene.ir import SceneIR
from ..export.api import export_scene
from ..export.base import ExportReport
from .jobs import FunctionJob, JobContext, JobHandle, Lane
from .jobs.tracked import TrackedJobs


@dataclass(frozen=True)
class ExportRequest:
    scene: SceneIR
    path: Path
    exporter: str
    options: dict[str, Any] = field(default_factory=dict)
    camera: Camera | None = None


def export_job(req: ExportRequest) -> Callable[[JobContext], ExportReport]:
    def run(ctx: JobContext) -> ExportReport:
        def cancelled() -> bool:
            return ctx.cancelled

        return export_scene(req.scene, req.path, req.exporter, req.options, req.camera, ctx.progress, cancelled)

    return run


class ExportService(TrackedJobs):
    progress = Signal(str, float, str)  # path, fraction, text
    finished = Signal(object)  # ExportReport
    failed = Signal(str, object)  # path, ErrorInfo

    def request(self, req: ExportRequest) -> JobHandle:
        job = FunctionJob(f"export {req.path.name}", Lane.IO, export_job(req), key=str(req.path))
        handle = self.submit_for(str(req.path), job)
        handle.progress.connect(self._on_progress)
        handle.finished.connect(self._on_finished)
        handle.failed.connect(self._on_failed)
        return handle

    @Slot(float, str)
    def _on_progress(self, fraction: float, text: str) -> None:
        self.progress.emit(self.sender_doc(), fraction, text)

    @Slot(object)
    def _on_finished(self, report: object) -> None:
        self.finished.emit(report)

    @Slot(object)
    def _on_failed(self, info: object) -> None:
        self.failed.emit(self.sender_doc(), info)
