"""JobRunner: one QThread worker per lane, latest-wins coalescing, signals for every outcome (docs/04 §1–2).

Workers emit JobHandle signals from their own thread; Qt queues them to receivers that are QObjects living
on the GUI thread. Connect handle signals to *bound slots of QObjects*, never to lambdas or free functions:
those would run on the worker thread. The GUI thread never waits on a job.
"""

from __future__ import annotations

import logging
import time

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot

from .job import ErrorInfo, Job, JobCancelled, JobContext, Lane

log = logging.getLogger(__name__)


class JobHandle(QObject):
    started = Signal()
    progress = Signal(float, str)
    partial = Signal(object)
    finished = Signal(object)
    failed = Signal(object)  # ErrorInfo
    cancelled = Signal()
    ended = Signal()  # after any of finished / failed / cancelled

    def __init__(self, job: Job) -> None:
        super().__init__()
        self.job = job
        self.context = JobContext(self.progress.emit, self.partial.emit)
        self.state = "pending"  # pending | running | finished | failed | cancelled
        self.seconds = 0.0

    def cancel(self) -> None:
        self.context.cancel()

    @property
    def done(self) -> bool:
        return self.state in ("finished", "failed", "cancelled")


class _Worker(QObject):
    @Slot(object)
    def execute(self, handle: JobHandle) -> None:
        if handle.context.cancelled:
            handle.state = "cancelled"
            handle.cancelled.emit()
            handle.ended.emit()
            return
        handle.state = "running"
        handle.started.emit()
        start = time.perf_counter()
        try:
            result = handle.job.run(handle.context)
        except JobCancelled:
            handle.state = "cancelled"
            handle.cancelled.emit()
        except Exception as exc:
            log.exception("job %s failed", handle.job.name)
            handle.state = "failed"
            handle.failed.emit(ErrorInfo.from_exception(exc))
        else:
            handle.state = "finished"
            handle.finished.emit(result)
        finally:
            handle.seconds = time.perf_counter() - start
            handle.ended.emit()


class _LaneThread(QObject):
    submit = Signal(object)

    def __init__(self, lane: Lane) -> None:
        super().__init__()
        self.qthread = QThread()
        self.qthread.setObjectName(f"structura-{lane.value}")
        self.worker = _Worker()
        self.worker.moveToThread(self.qthread)
        self.submit.connect(self.worker.execute)  # queued: the worker lives in the lane thread
        self.qthread.start()

    def stop(self, timeout_ms: int) -> None:
        self.qthread.quit()
        self.qthread.wait(timeout_ms)


class JobRunner(QObject):
    job_submitted = Signal(object)  # JobHandle (Activity panel)
    _dispatch = Signal(object)  # queued to ourselves: jobs start only after submit()'s caller has connected

    def __init__(self, lanes: tuple[Lane, ...] = tuple(Lane)) -> None:
        super().__init__()
        self._lanes = {lane: _LaneThread(lane) for lane in lanes}
        self._latest: dict[tuple[Lane, str], JobHandle] = {}
        self._live: set[JobHandle] = set()
        self._dispatch.connect(self._start, Qt.ConnectionType.QueuedConnection)

    def submit(self, job: Job) -> JobHandle:
        handle = JobHandle(job)
        if job.key is not None:
            previous = self._latest.get((job.lane, job.key))
            if previous is not None and not previous.done:
                previous.cancel()
            self._latest[(job.lane, job.key)] = handle
        self._live.add(handle)  # keep the handle alive until it reports an outcome
        handle.ended.connect(self._forget)  # a slot of a GUI-thread QObject: queued, runs on the GUI thread
        self.job_submitted.emit(handle)
        self._dispatch.emit(handle)  # a job must not finish before the caller connects to its signals
        return handle

    @Slot(object)
    def _start(self, handle: JobHandle) -> None:
        self._lanes[handle.job.lane].submit.emit(handle)

    @Slot()
    def _forget(self) -> None:
        handle = self.sender()
        if isinstance(handle, JobHandle):
            self._live.discard(handle)

    def cancel_all(self) -> None:
        for handle in list(self._live):
            handle.cancel()

    def shutdown(self, timeout_ms: int = 2000) -> None:
        self.cancel_all()
        for lane in self._lanes.values():
            lane.stop(timeout_ms)

    def active(self) -> list[JobHandle]:
        return [h for h in self._live if not h.done]

    def lane_thread(self, lane: Lane) -> QThread:
        return self._lanes[lane].qthread
