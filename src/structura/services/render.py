"""RenderService: progressive precision renders on the device lane (docs/04 §5.2)."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, replace

import numpy as np
from PySide6.QtCore import Signal, Slot

from ..compute.base import Backend, device_details, device_label
from ..compute.select import select_backend
from ..core.scene.camera import Camera
from ..core.scene.ir import SceneIR
from ..render.api import RenderProgress, prepare_with_frame, progressive
from ..render.denoise import denoise_with
from ..render.details import RenderDetails, render_details
from ..render.output import Display
from ..render.settings import RenderSettings
from .jobs import FunctionJob, JobContext, JobHandle, JobRunner, Lane
from .jobs.tracked import TrackedJobs


@dataclass(frozen=True)
class RenderRequest:
    """A render to run on the device lane.

    Attributes:
        doc_id: Who asked (results carry it; a new request for the same id replaces the running one).
        scene: The built scene.
        settings: The render settings.
        device: The compute device ('auto', 'cuda' …).
        camera: The camera; None uses the script's camera, or frames the structure.
        tag_presets: Whether tags named like presets use them.
        denoise: A render.denoise method to run on the compute lane once the render finishes, or None.
        display: How to tone-map each pass in the job (the GUI thread then only shows it), or None.
        resume: A stopped render of the same scene, camera and settings to continue.
    """

    doc_id: str
    scene: SceneIR
    settings: RenderSettings
    device: str = "auto"
    camera: Camera | None = None
    tag_presets: bool = False
    denoise: str | None = None
    display: Display | None = None
    resume: RenderProgress | None = None


@dataclass(frozen=True)
class RenderUpdate:
    """A render's progress as the GUI sees it.

    Attributes:
        progress: The render progress (linear image, samples, timings).
        device: The backend and device that rendered it.
        total_samples: The samples the render aims for.
        denoised: The denoised image, once denoising ran.
        denoiser: The method that produced ``denoised``.
        display: uint8 (H, W, 3) of ``progress.image``, made off the GUI thread for ``display_for``.
        display_for: The Display ``display`` and ``denoised_display`` were made with.
        details: What the render used (reports).
        denoised_display: uint8 display image of ``denoised`` (for ``display_for``).
        passes: Passes so far.
    """

    progress: RenderProgress
    device: str
    total_samples: int
    denoised: np.ndarray | None = None
    denoiser: str = ""
    display: np.ndarray | None = None
    display_for: Display | None = None
    details: RenderDetails | None = None
    denoised_display: np.ndarray | None = None
    passes: int = 0

    @property
    def fraction(self) -> float:
        """How far the render is, 0 … 1 (buckets done for the tiled sampler, else samples)."""
        if self.progress.completed is not None:  # the tiled sampler counts buckets
            return self.progress.completed
        return self.progress.samples / max(1, self.total_samples)


class DeviceBackends:
    """Backends are created and used on the device lane only (CUDA contexts are per thread)."""

    def __init__(self) -> None:
        self._cache: dict[str, Backend] = {}

    def get(self, name: str) -> Backend:
        """Returns the backend of a device, created on first use (on the device lane).

        Args:
            name: A compute.select name ('auto', 'cpu', 'cuda' …).
        """
        if name not in self._cache:
            self._cache[name] = select_backend(name)
        return self._cache[name]


def _display(image: np.ndarray, display: Display | None) -> np.ndarray | None:
    """The read-only 8-bit image of ``image`` for ``display`` (None without a display)."""
    if display is None:
        return None
    out = np.ascontiguousarray(display.apply(image))
    out.flags.writeable = False
    return out


def render_job(req: RenderRequest, backends: DeviceBackends) -> Callable[[JobContext], RenderUpdate]:
    """Makes the device-lane job of a render request.

    Args:
        req: The request.
        backends: The device lane's backends.

    Returns:
        The job function: it reports phases before the first pass, publishes an update after every pass
        (``partial``) and returns the last one.
    """

    def run(ctx: JobContext) -> RenderUpdate:
        """Prepares, renders pass by pass and publishes each pass."""

        def phase(text: str) -> None:  # before the first pass: what the render is doing (the view shows it)
            """Reports what the render is doing before its first pass (and honours a cancel)."""
            ctx.progress(0.0, text, force=True)
            ctx.check_cancelled()

        phase("Preparing the render device…")
        backend = backends.get(req.device)
        started = time.perf_counter()
        prepared, frame = prepare_with_frame(req.scene, req.settings, req.tag_presets, req.camera, phase)
        details = render_details(prepared, frame, time.perf_counter() - started, device_details(backend))
        ctx.check_cancelled()
        label, update = device_label(backend), None
        results = progressive(prepared, req.settings, backend, frame, ctx.check_cancelled, req.resume, phase)
        for passes, result in enumerate(results, 1):
            result.image.flags.writeable = False
            update = RenderUpdate(result, label, req.settings.samples, display=_display(result.image, req.display),
                                  display_for=req.display, details=details, passes=passes)  # fmt: skip
            ctx.partial(update)
            ctx.check_cancelled()
        if update is None:  # a resumed render that had already finished: nothing more to sample
            assert req.resume is not None
            update = RenderUpdate(req.resume, label, req.settings.samples, details=details)
        return update

    return run


def denoise_job(update: RenderUpdate, method: str) -> Callable[[JobContext], RenderUpdate]:
    """Makes the compute-lane job that denoises a finished render.

    Args:
        update: The finished render.
        method: A render.denoise method ('auto', 'oidn', 'atrous').

    Returns:
        The job function; its result is ``update`` with the denoised image (tone-mapped too).
    """

    def run(ctx: JobContext) -> RenderUpdate:
        """Denoises and tone-maps the result for the update's display."""
        image, used = denoise_with(update.progress.image, update.progress.aovs, method)
        image.flags.writeable = False
        shown = _display(image, update.display_for)  # tone-mapped here, not on the GUI thread
        return replace(update, denoised=image, denoiser=used, denoised_display=shown)

    return run


def display_job(update: RenderUpdate, display: Display) -> Callable[[JobContext], RenderUpdate]:
    """Makes the job that tone-maps a finished image again, for another exposure, view or look.

    Bloom on a large image takes a moment, so this runs off the GUI thread.

    Args:
        update: The render to show.
        display: The new exposure, view and look.

    Returns:
        The job function; its result is ``update`` with the new display images.
    """

    def run(ctx: JobContext) -> RenderUpdate:
        """Tone-maps the image and the denoised image."""
        shown = _display(update.progress.image, display)
        ctx.check_cancelled()
        denoised = _display(update.denoised, display) if update.denoised is not None else None
        return replace(update, display=shown, display_for=display, denoised_display=denoised)

    return run


class RenderService(TrackedJobs):
    """Runs renders, denoising and re-tone-mapping as jobs; one latest-wins render per document.

    Signals carry the document id: ``phase`` before the first pass, ``progress`` after each pass, ``finished``
    with the final update (after denoising when asked for), ``failed``, ``cancelled``, and ``displayed`` /
    ``display_failed`` for ``redisplay`` jobs.
    """

    progress = Signal(str, object)  # doc_id, RenderUpdate
    phase = Signal(str, str)  # doc_id, what the render is doing before its first pass
    finished = Signal(str, object)  # doc_id, RenderUpdate
    failed = Signal(str, object)  # doc_id, ErrorInfo
    cancelled = Signal(str)
    displayed = Signal(str, object)  # doc_id, the RenderUpdate tone-mapped again by redisplay()
    display_failed = Signal(str, object)  # doc_id, ErrorInfo of a failed redisplay()

    def __init__(self, runner: JobRunner) -> None:
        super().__init__(runner)
        self.backends = DeviceBackends()  # shared with the other device-lane services (animation)
        self._denoise_after: dict[JobHandle, str] = {}

    def request(self, req: RenderRequest) -> JobHandle:
        """Starts a render (it replaces a running render of the same document).

        Args:
            req: The request.

        Returns:
            The job's handle.
        """
        job = FunctionJob(f"render {req.doc_id}", Lane.DEVICE, render_job(req, self.backends), key=req.doc_id)
        handle = self._track(req.doc_id, job)
        handle.partial.connect(self._on_partial)
        handle.progress.connect(self._on_phase)
        if req.denoise:
            self._denoise_after[handle] = req.denoise
            handle.ended.connect(self._forget_denoise)  # a bound slot: queued to the GUI thread
        return handle

    def denoise(self, doc_id: str, update: RenderUpdate, method: str = "auto") -> JobHandle:
        """Denoises a finished render on the compute lane; ``finished`` carries the result.

        Args:
            doc_id: The document.
            update: The finished render.
            method: A render.denoise method.

        Returns:
            The job's handle.
        """
        job = FunctionJob(f"denoise {doc_id}", Lane.COMPUTE, denoise_job(update, method), key=doc_id)
        return self._track(doc_id, job)

    def redisplay(self, doc_id: str, update: RenderUpdate, display: Display) -> JobHandle:
        """Tone-maps a finished render again on the compute lane (the latest request wins).

        Args:
            doc_id: The document.
            update: The render to show.
            display: The new exposure, view and look.

        Returns:
            The job's handle; ``displayed`` carries the result, ``display_failed`` an error.
        """
        job = FunctionJob(f"display {doc_id}", Lane.COMPUTE, display_job(update, display), key=f"{doc_id}:display")
        handle = self.submit_for(doc_id, job)
        handle.finished.connect(self._on_displayed)
        handle.failed.connect(self._on_display_failed)
        return handle

    @Slot(object)
    def _on_displayed(self, update: object) -> None:
        self.displayed.emit(self.sender_doc(), update)

    @Slot(object)
    def _on_display_failed(self, info: object) -> None:
        self.display_failed.emit(self.sender_doc(), info)

    def _track(self, doc_id: str, job: FunctionJob) -> JobHandle:
        handle = self.submit_for(doc_id, job)
        handle.finished.connect(self._on_finished)
        handle.failed.connect(self._on_failed)
        handle.cancelled.connect(self._on_cancelled)
        return handle

    @Slot(float, str)
    def _on_phase(self, _fraction: float, text: str) -> None:
        if text:
            self.phase.emit(self.sender_doc(), text)

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
