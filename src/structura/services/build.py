"""BuildService: latest-wins scene builds on the build lane, in resumable slices (docs/04 §3–4)."""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass

import psutil
from PySide6.QtCore import Signal, Slot

from ..core.build.api import iter_build, scene_of
from ..core.build.driver import BuildSession, BuildStats
from ..core.lang.compile.program import RuleProgram
from ..core.scene.ir import SceneIR
from .jobs import ErrorInfo, FunctionJob, JobContext, JobHandle, Lane
from .jobs.tracked import TrackedJobs

SLICE = 20_000  # rule applications per slice (≈ 10–20 ms)
PROGRESS_INTERVAL = 0.05  # seconds between progress reports
PREVIEW_OBJECTS = 250_000  # the object cap while a parameter slider is being dragged (docs/04 §4)


@dataclass(frozen=True)
class BuildLimits:
    """Build ▸ Build Limits…: caps on top of the script's own 'set maxobjects' / 'set maxdepth'."""

    max_objects: int = 0  # stop after this many objects (0: no extra cap)
    memory_percent: int = 50  # stop before the build's buffers need more than this share of the free memory
    time_limit: float = 0.0  # seconds (0: none)

    def capped(self, objects: int) -> BuildLimits:
        cap = min(self.max_objects, objects) if self.max_objects else objects
        return BuildLimits(cap, self.memory_percent, self.time_limit)

    def reason(self, session: BuildSession, seconds: float, memory: int) -> str:
        """Why the build must stop now ('' = go on)."""
        if self.max_objects and session.emitted >= self.max_objects:
            return f"the object limit ({self.max_objects:,})"
        if self.time_limit and seconds >= self.time_limit:
            return f"the time limit ({self.time_limit:g} s)"
        if session.memory_bytes() > memory:
            return f"the memory guard ({self.memory_percent} % of the free memory)"
        return ""


@dataclass(frozen=True)
class BuildRequest:
    doc_id: str
    program: RuleProgram
    seed: int = 0
    limits: BuildLimits = BuildLimits()
    digest: str = ""  # the analysis digest (equal digests build equal scenes): the SceneCache key


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
    stopped: str = ""  # the limit that ended the build early ('' = it finished)
    limits: BuildLimits = BuildLimits()
    digest: str = ""


CacheKey = tuple[str, int, BuildLimits]


class SceneCache:
    """Recent finished builds by (digest, seed, limits) (docs/06 §10.5, docs/16 §2.2): undoing a parameter
    change or scrubbing the timeline back shows the earlier scene at once. Bounded by entries and objects."""

    def __init__(self, entries: int = 8, objects: int = 4_000_000) -> None:
        self.entries, self.objects = entries, objects
        self._items: OrderedDict[CacheKey, BuildOutcome] = OrderedDict()

    def get(self, key: CacheKey) -> BuildOutcome | None:
        outcome = self._items.get(key)
        if outcome is not None:
            self._items.move_to_end(key)
        return outcome

    def put(self, outcome: BuildOutcome) -> None:
        if not outcome.digest or outcome.stopped or len(outcome.scene) > self.objects:
            return
        self._items[(outcome.digest, outcome.seed, outcome.limits)] = outcome
        self._items.move_to_end((outcome.digest, outcome.seed, outcome.limits))
        while len(self._items) > self.entries or sum(len(o.scene) for o in self._items.values()) > self.objects:
            self._items.popitem(last=False)


def build_job(req: BuildRequest) -> Callable[[JobContext], BuildOutcome]:
    def run(ctx: JobContext) -> BuildOutcome:
        start = last = time.perf_counter()
        memory = psutil.virtual_memory().available * max(1, min(100, req.limits.memory_percent)) // 100
        session, stopped = None, ""
        for session in iter_build(req.program, req.seed, SLICE):
            ctx.check_cancelled()
            now = time.perf_counter()
            stopped = req.limits.reason(session, now - start, memory)
            if stopped:
                break
            if now - last >= PROGRESS_INTERVAL:
                last, stats = now, session.stats()
                ctx.partial(BuildProgress(stats.objects, stats.generations, now - start))
        assert session is not None
        return BuildOutcome(req.doc_id, scene_of(session), session.stats(), req.seed, stopped, req.limits,
                            req.digest)  # fmt: skip

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
