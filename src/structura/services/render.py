"""RenderService: progressive precision renders on the device lane (docs/04 §5.2)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from PySide6.QtCore import Signal, Slot

from ..compute.base import Backend
from ..compute.select import select_backend
from ..core.scene.camera import Camera
from ..core.scene.ir import SceneIR
from ..render.api import RenderProgress, prepare, progressive
from ..render.config import scene_frame
from ..render.settings import RenderSettings
from .jobs import FunctionJob, JobContext, JobHandle, JobRunner, Lane
from .jobs.tracked import TrackedJobs


@dataclass(frozen=True)
class RenderRequest:
    doc_id: str
    scene: SceneIR
    settings: RenderSettings
    device: str = "auto"
    camera: Camera | None = None  # None: the script camera (or framed)
    tag_presets: bool = False


@dataclass(frozen=True)
class RenderUpdate:
    progress: RenderProgress
    device: str
    total_samples: int

    @property
    def fraction(self) -> float:
        return self.progress.samples / max(1, self.total_samples)


class _Backends:
    """Backends are created and used on the device lane only (CUDA contexts are per thread)."""

    def __init__(self) -> None:
        self._cache: dict[str, Backend] = {}

    def get(self, name: str) -> Backend:
        if name not in self._cache:
            self._cache[name] = select_backend(name)
        return self._cache[name]


def render_job(req: RenderRequest, backends: _Backends) -> Callable[[JobContext], RenderUpdate]:
    def run(ctx: JobContext) -> RenderUpdate:
        backend = backends.get(req.device)
        prepared = prepare(req.scene, tag_presets=req.tag_presets)
        ctx.check_cancelled()
        frame = scene_frame(prepared.scene_settings, req.settings, prepared.lo, prepared.hi, prepared.declarations)
        if req.camera is not None:
            frame = replace(frame, camera=req.camera)
        update = None
        for result in progressive(prepared, req.settings, backend, frame):
            result.image.flags.writeable = False
            update = RenderUpdate(result, f"{backend.name} {backend.device_name}".strip(), req.settings.samples)
            ctx.partial(update)
            ctx.check_cancelled()
        assert update is not None
        return update

    return run


class RenderService(TrackedJobs):
    progress = Signal(str, object)  # doc_id, RenderUpdate
    finished = Signal(str, object)  # doc_id, RenderUpdate
    failed = Signal(str, object)  # doc_id, ErrorInfo
    cancelled = Signal(str)

    def __init__(self, runner: JobRunner) -> None:
        super().__init__(runner)
        self._backends = _Backends()

    def request(self, req: RenderRequest) -> JobHandle:
        job = FunctionJob(f"render {req.doc_id}", Lane.DEVICE, render_job(req, self._backends), key=req.doc_id)
        handle = self.submit_for(req.doc_id, job)
        handle.partial.connect(self._on_partial)
        handle.finished.connect(self._on_finished)
        handle.failed.connect(self._on_failed)
        handle.cancelled.connect(self._on_cancelled)
        return handle

    @Slot(object)
    def _on_partial(self, update: object) -> None:
        self.progress.emit(self.sender_doc(), update)

    @Slot(object)
    def _on_finished(self, update: object) -> None:
        self.finished.emit(self.sender_doc(), update)

    @Slot(object)
    def _on_failed(self, info: object) -> None:
        self.failed.emit(self.sender_doc(), info)

    @Slot()
    def _on_cancelled(self) -> None:
        self.cancelled.emit(self.sender_doc())
