"""AnimationService: render a timeline to numbered frames (and a video) on the device lane (docs/16 §2.3)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PySide6.QtCore import Signal, Slot

from ..render.animation import Animation, frame_path, render_frame
from ..render.output import save_image, to_display
from ..render.video import encode_video
from .jobs import FunctionJob, JobContext, JobHandle, JobRunner, Lane
from .jobs.tracked import TrackedJobs
from .render import DeviceBackends

DOC = "animation"


@dataclass(frozen=True)
class AnimationRequest:
    animation: Animation
    frames: range
    pattern: Path  # frames are written as <stem>_0000<suffix> next to it
    video: Path | None = None
    device: str = "auto"


@dataclass(frozen=True)
class AnimationProgress:
    frame: int
    done: int
    total: int
    image: np.ndarray  # float32 (H, W, 3) linear
    path: Path


def animation_job(req: AnimationRequest, backends: DeviceBackends) -> Callable[[JobContext], list[Path]]:
    def run(ctx: JobContext) -> list[Path]:
        backend = backends.get(req.device)
        req.pattern.parent.mkdir(parents=True, exist_ok=True)
        written, shown = [], []
        for index, frame in enumerate(req.frames):
            result, settings = render_frame(req.animation, frame, backend, ctx.check_cancelled)
            path = frame_path(req.pattern, frame)
            save_image(result.image, path, 0.0, settings.view_transform)
            written.append(path)
            if req.video is not None:
                shown.append(to_display(result.image, 0.0, settings.view_transform))
            result.image.flags.writeable = False
            ctx.partial(AnimationProgress(frame, index + 1, len(req.frames), result.image, path))
            ctx.check_cancelled()
        if req.video is not None:
            encode_video(req.video, shown, req.animation.timeline.fps)
            written.append(req.video)
        return written

    return run


class AnimationService(TrackedJobs):
    progress = Signal(object)  # AnimationProgress
    finished = Signal(object)  # list[Path]
    failed = Signal(object)  # ErrorInfo
    cancelled = Signal()

    def __init__(self, runner: JobRunner, backends: DeviceBackends) -> None:
        super().__init__(runner)
        self._backends = backends

    def request(self, req: AnimationRequest) -> JobHandle:
        job = FunctionJob(f"animation {req.pattern.name}", Lane.DEVICE, animation_job(req, self._backends), key=DOC)
        handle = self.submit_for(DOC, job)
        handle.partial.connect(self._on_partial)
        handle.finished.connect(self._on_finished)
        handle.failed.connect(self.failed)
        handle.cancelled.connect(self.cancelled)
        return handle

    def cancel_all(self) -> None:
        self.cancel(DOC)

    @Slot(object)
    def _on_partial(self, progress: object) -> None:
        self.progress.emit(progress)

    @Slot(object)
    def _on_finished(self, paths: object) -> None:
        self.finished.emit(paths)
