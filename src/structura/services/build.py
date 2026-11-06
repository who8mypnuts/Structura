"""BuildService: latest-wins scene builds on the build lane, in resumable slices (docs/04 §3–4)."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import Signal, Slot

from ..core.build.api import iter_build, scene_of
from ..core.build.driver import BuildStats
from ..core.lang.compile.program import RuleProgram
from ..core.scene.ir import SceneIR
from .jobs import ErrorInfo, FunctionJob, JobContext, JobHandle, Lane
from .jobs.tracked import TrackedJobs

SLICE = 20_000  # rule applications per slice (≈ 10–20 ms)
PROGRESS_INTERVAL = 0.05  # seconds between progress reports


@dataclass(frozen=True)
class BuildRequest:
    doc_id: str
    program: RuleProgram
    seed: int = 0


@dataclass(frozen=True)
class BuildProgress:
    objects: int
    generation: int
    seconds: float


@dataclass(frozen=True)
class BuildOutcome:
    doc_id: str
    scene: SceneIR
    stats: BuildStats
    seed: int


def build_job(req: BuildRequest) -> Callable[[JobContext], BuildOutcome]:
    def run(ctx: JobContext) -> BuildOutcome:
        start = last = time.perf_counter()
        session = None
        for session in iter_build(req.program, req.seed, SLICE):
            ctx.check_cancelled()
            now = time.perf_counter()
            if now - last >= PROGRESS_INTERVAL:
                last, stats = now, session.stats()
                ctx.partial(BuildProgress(stats.objects, stats.generations, now - start))
        assert session is not None
        return BuildOutcome(req.doc_id, scene_of(session), session.stats(), req.seed)

    return run


class BuildService(TrackedJobs):
    started = Signal(str)
    progress = Signal(str, object)  # doc_id, BuildProgress
    finished = Signal(str, object)  # doc_id, BuildOutcome
    failed = Signal(str, object)  # doc_id, ErrorInfo

    def request(self, req: BuildRequest) -> JobHandle:
        job = FunctionJob(f"build {req.doc_id}", Lane.BUILD, build_job(req), key=req.doc_id)
        handle = self.submit_for(req.doc_id, job)
        handle.started.connect(self._on_started)
        handle.partial.connect(self._on_partial)
        handle.finished.connect(self._on_finished)
        handle.failed.connect(self._on_failed)
        return handle

    @Slot()
    def _on_started(self) -> None:
        self.started.emit(self.sender_doc())

    @Slot(object)
    def _on_partial(self, progress: object) -> None:
        self.progress.emit(self.sender_doc(), progress)

    @Slot(object)
    def _on_finished(self, outcome: object) -> None:
        self.finished.emit(self.sender_doc(), outcome)

    @Slot(object)
    def _on_failed(self, info: object) -> None:
        self.failed.emit(self.sender_doc(), info if isinstance(info, ErrorInfo) else ErrorInfo(str(info)))
