"""Shared bookkeeping for services that run one latest-wins job per document."""

from __future__ import annotations

from PySide6.QtCore import QObject, Slot

from .job import Job
from .runner import JobHandle, JobRunner


class TrackedJobs(QObject):
    """Remembers which document each running handle belongs to; subclasses connect their own slots."""

    def __init__(self, runner: JobRunner) -> None:
        super().__init__()
        self.runner = runner
        self._handles: dict[JobHandle, str] = {}

    def submit_for(self, doc_id: str, job: Job) -> JobHandle:
        handle = self.runner.submit(job)
        self._handles[handle] = doc_id
        handle.ended.connect(self._on_ended)
        return handle

    def cancel(self, doc_id: str) -> None:
        for handle, doc in self._handles.items():
            if doc == doc_id:
                handle.cancel()

    def busy(self, doc_id: str) -> bool:
        return any(doc == doc_id and not h.done for h, doc in self._handles.items())

    def sender_doc(self) -> str:
        """The document of the handle whose signal is being delivered."""
        sender = self.sender()
        return self._handles.get(sender, "") if isinstance(sender, JobHandle) else ""

    @Slot()
    def _on_ended(self) -> None:
        sender = self.sender()
        if isinstance(sender, JobHandle):
            self._handles.pop(sender, None)
