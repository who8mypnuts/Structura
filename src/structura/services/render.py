"""RenderService: progressive precision renders on the device lane (docs/04 §5.2)."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, replace

import numpy as np
from PySide6.QtCore import Signal, Slot

from ..compute.base import Backend
from ..compute.select import select_backend
from ..core.scene.camera import Camera
from ..core.scene.ir import SceneIR
from ..render.api import RenderProgress, prepare_with_frame, progressive
from ..render.denoise import denoise_with
from ..render.details import RenderDetails, render_details
from ..render.output import to_display
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
    denoise: str | None = None  # a render.denoise method, run on the compute lane once the render finishes
    display: tuple[float, str] | None = None  # (exposure, view): also make the 8-bit display image in the job
    resume: RenderProgress | None = None  # continue a stopped render (same scene, camera and settings)


@dataclass(frozen=True)
class RenderUpdate:
    progress: RenderProgress
    device: str
    total_samples: int
    denoised: np.ndarray | None = None
    denoiser: str = ""  # the method that produced ``denoised``
    display: np.ndarray | None = None  # uint8 (H, W, 3) for RenderRequest.display, made off the GUI thread
    display_for: tuple[float, str] | None = None  # the (exposure, view) ``display`` was made with
    details: RenderDetails | None = None  # what the render used (reports)
    denoised_display: np.ndarray | None = None  # uint8 display image of ``denoised`` (for ``display_for``)
    passes: int = 0

    @property
    def fraction(self) -> float:
        return self.progress.samples / max(1, self.total_samples)


class DeviceBackends:
    """Backends are created and used on the device lane only (CUDA contexts are per thread)."""

    def __init__(self) -> None:
        self._cache: dict[str, Backend] = {}

    def get(self, name: str) -> Backend:
        if name not in self._cache:
            self._cache[name] = select_backend(name)
        return self._cache[name]


def _display(image: np.ndarray, display: tuple[float, str] | None) -> np.ndarray | None:
    if display is None:
        return None
    out = np.ascontiguousarray(to_display(image, *display))
    out.flags.writeable = False
    return out


def render_job(req: RenderRequest, backends: DeviceBackends) -> Callable[[JobContext], RenderUpdate]:
    def run(ctx: JobContext) -> RenderUpdate:
        backend = backends.get(req.device)
        started = time.perf_counter()
        prepared, frame = prepare_with_frame(req.scene, req.settings, req.tag_presets, req.camera)
        details = render_details(prepared, frame, time.perf_counter() - started)
        ctx.check_cancelled()
        update = None
        results = progressive(prepared, req.settings, backend, frame, ctx.check_cancelled, req.resume)
        for passes, result in enumerate(results, 1):
            result.image.flags.writeable = False
            update = RenderUpdate(result, f"{backend.name} {backend.device_name}".strip(), req.settings.samples,
                                  display=_display(result.image, req.display), display_for=req.display,
                                  details=details, passes=passes)  # fmt: skip
            ctx.partial(update)
            ctx.check_cancelled()
        if update is None:  # a resumed render that had already finished: nothing more to sample
            assert req.resume is not None
            update = RenderUpdate(req.resume, f"{backend.name} {backend.device_name}".strip(), req.settings.samples,
                                  details=details)  # fmt: skip
        return update

    return run


def denoise_job(update: RenderUpdate, method: str) -> Callable[[JobContext], RenderUpdate]:
    def run(ctx: JobContext) -> RenderUpdate:
        image, used = denoise_with(update.progress.image, update.progress.aovs, method)
        image.flags.writeable = False
        shown = _display(image, update.display_for)  # tone-mapped here, not on the GUI thread
        return replace(update, denoised=image, denoiser=used, denoised_display=shown)

    return run


class RenderService(TrackedJobs):
    progress = Signal(str, object)  # doc_id, RenderUpdate
    finished = Signal(str, object)  # doc_id, RenderUpdate
    failed = Signal(str, object)  # doc_id, ErrorInfo
    cancelled = Signal(str)

    def __init__(self, runner: JobRunner) -> None:
        super().__init__(runner)
        self.backends = DeviceBackends()  # shared with the other device-lane services (animation)
        self._denoise_after: dict[JobHandle, str] = {}

    def request(self, req: RenderRequest) -> JobHandle:
        job = FunctionJob(f"render {req.doc_id}", Lane.DEVICE, render_job(req, self.backends), key=req.doc_id)
        handle = self._track(req.doc_id, job)
        handle.partial.connect(self._on_partial)
        if req.denoise:
            self._denoise_after[handle] = req.denoise
            handle.ended.connect(self._forget_denoise)  # a bound slot: queued to the GUI thread
        return handle

    def denoise(self, doc_id: str, update: RenderUpdate, method: str = "auto") -> JobHandle:
        """Denoise a finished render on the compute lane (parallel Numba); ``finished`` carries the result."""
        job = FunctionJob(f"denoise {doc_id}", Lane.COMPUTE, denoise_job(update, method), key=doc_id)
        return self._track(doc_id, job)

    def _track(self, doc_id: str, job: FunctionJob) -> JobHandle:
        handle = self.submit_for(doc_id, job)
        handle.finished.connect(self._on_finished)
        handle.failed.connect(self._on_failed)
        handle.cancelled.connect(self._on_cancelled)
        return handle

    @Slot(object)
    def _on_partial(self, update: object) -> None:
        self.progress.emit(self.sender_doc(), update)

    @Slot(object)
    def _on_finished(self, update: object) -> None:
        method = self._denoise_after.pop(self.sender(), None)  # type: ignore[call-overload]
        if method and isinstance(update, RenderUpdate):
            self.progress.emit(self.sender_doc(), update)  # show the raw result while the denoiser runs
            self.denoise(self.sender_doc(), update, method)
            return
        self.finished.emit(self.sender_doc(), update)

    @Slot()
    def _forget_denoise(self) -> None:
        self._denoise_after.pop(self.sender(), None)  # type: ignore[call-overload]

    @Slot(object)
    def _on_failed(self, info: object) -> None:
        self.failed.emit(self.sender_doc(), info)

    @Slot()
    def _on_cancelled(self) -> None:
        self.cancelled.emit(self.sender_doc())
