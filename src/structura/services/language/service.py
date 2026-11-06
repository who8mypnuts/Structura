"""Debounced analysis on the analysis lane; results are immutable ``Analysis`` snapshots (docs/04 §4)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from ...core.lang.analysis import Analysis, analyze
from ..jobs import FunctionJob, JobContext, JobRunner, Lane

DEBOUNCE_MS = 120


@dataclass(frozen=True)
class AnalysisRequest:
    doc_id: str
    text: str
    version: int
    seed: int = 0
    params: tuple[tuple[str, float], ...] = ()
    script_dir: Path | None = None


class LanguageService(QObject):
    analysis_ready = Signal(str, object)  # doc_id, Analysis

    def __init__(self, runner: JobRunner, debounce_ms: int = DEBOUNCE_MS) -> None:
        super().__init__()
        self.runner = runner
        self._pending: dict[str, AnalysisRequest] = {}
        self._latest: dict[str, Analysis] = {}
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(debounce_ms)
        self._timer.timeout.connect(self._flush)

    def request(self, req: AnalysisRequest, immediate: bool = False) -> None:
        """Queue an analysis; edits arriving within the debounce interval coalesce into one job."""
        self._pending[req.doc_id] = req
        if immediate:
            self._flush()
        else:
            self._timer.start()

    def latest(self, doc_id: str) -> Analysis | None:
        return self._latest.get(doc_id)

    @Slot()
    def _flush(self) -> None:
        pending, self._pending = self._pending, {}
        for req in pending.values():
            job = FunctionJob(f"analyse {req.doc_id}", Lane.ANALYSIS, _runner_for(req), key=req.doc_id)
            handle = self.runner.submit(job)
            handle.finished.connect(self._on_finished)

    @Slot(object)
    def _on_finished(self, result: object) -> None:
        doc_id, analysis = result if isinstance(result, tuple) else ("", None)
        if not isinstance(analysis, Analysis):
            return
        current = self._latest.get(doc_id)
        if current is not None and current.version > analysis.version:
            return  # a newer analysis already arrived
        self._latest[doc_id] = analysis
        self.analysis_ready.emit(doc_id, analysis)


def _runner_for(req: AnalysisRequest) -> Callable[[JobContext], tuple[str, Analysis]]:
    def run(ctx: JobContext) -> tuple[str, Analysis]:
        ctx.check_cancelled()
        return req.doc_id, analyze(req.text, req.seed, dict(req.params), req.script_dir, req.version)

    return run
