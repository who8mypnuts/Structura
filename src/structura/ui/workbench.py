"""Workbench: connects documents, services and views (docs/02 §5). Holds no domain logic; it schedules.

Text edits → debounced analysis → (live mode) latest-wins build → preview upload on the io lane → viewport.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from ..core.lang.analysis import Analysis
from ..core.scene.settings import settings_from_events
from ..preview.instances import PreviewScene, preview_scene
from ..services.build import BuildOutcome, BuildProgress, BuildRequest, BuildService
from ..services.jobs import ErrorInfo, FunctionJob, JobContext, JobRunner, Lane
from ..services.language import LanguageService
from ..services.language.service import AnalysisRequest
from .documents import DocumentTabs, EditorTab

log = logging.getLogger("structura.ui")
MAX_SEED = 32767  # Structure Synth's seed range (auto-increment wraps here)


@dataclass(frozen=True)
class PreviewReady:
    doc_id: str
    outcome: BuildOutcome
    preview: PreviewScene


class Workbench(QObject):
    analysis_shown = Signal(object, object)  # EditorTab, Analysis
    build_started = Signal(object)  # EditorTab
    build_progress = Signal(object, object)  # EditorTab, BuildProgress
    scene_ready = Signal(object, object, object, object, bool)  # tab, BuildOutcome, PreviewScene, Camera|None, frame
    message = Signal(str)

    def __init__(self, tabs: DocumentTabs, runner: JobRunner) -> None:
        super().__init__()
        self.tabs, self.runner = tabs, runner
        self.language = LanguageService(runner)
        self.builds = BuildService(runner)
        self.live = True
        self._build_after_analysis: set[str] = set()
        tabs.tab_edited.connect(self.on_edited)
        tabs.current_tab_changed.connect(self.on_current)
        self.language.analysis_ready.connect(self.on_analysis)
        self.builds.started.connect(self.on_build_started)
        self.builds.progress.connect(self.on_build_progress)
        self.builds.finished.connect(self.on_build_finished)
        self.builds.failed.connect(self.on_build_failed)

    def tab(self, doc_id: str) -> EditorTab | None:
        return next((t for t in self.tabs.tabs() if t.doc_id == doc_id), None)

    # -- analysis ------------------------------------------------------------------------------------------
    def analyze(self, tab: EditorTab, immediate: bool = False) -> None:
        script_dir = tab.path.parent if tab.path else None
        params = tuple(sorted(tab.params.items()))
        req = AnalysisRequest(tab.doc_id, tab.text(), tab.version, tab.seed, params, script_dir)
        self.language.request(req, immediate)

    @Slot(object)
    def on_edited(self, tab: EditorTab) -> None:
        self.analyze(tab)

    @Slot(object)
    def on_current(self, tab: EditorTab | None) -> None:
        if tab is None:
            return
        if tab.analysis is not None:
            self.analysis_shown.emit(tab, tab.analysis)
        else:
            self.analyze(tab, immediate=True)

    @Slot(str, object)
    def on_analysis(self, doc_id: str, analysis: object) -> None:
        tab = self.tab(doc_id)
        if tab is None or not isinstance(analysis, Analysis) or analysis.version != tab.version:
            return  # closed, or an older version of the text
        tab.analysis = analysis
        if analysis.rules or analysis.program is not None:
            tab.editor.analysis = analysis  # keep the last parsed symbols while the text has errors
        tab.editor.set_diagnostics(list(analysis.diagnostics))
        self.analysis_shown.emit(tab, analysis)
        wanted = doc_id in self._build_after_analysis
        self._build_after_analysis.discard(doc_id)
        if analysis.ok and (wanted or (self.live and analysis.digest != tab.built_digest)):
            self._start_build(tab, analysis)

    # -- building ------------------------------------------------------------------------------------------
    def build(self, tab: EditorTab | None = None) -> None:
        """F5: build the current text now (re-analysing first when the analysis is stale)."""
        tab = tab or self.tabs.current()
        if tab is None:
            return
        if tab.analysis is not None and tab.analysis.version == tab.version and tab.analysis.ok:
            self._start_build(tab, tab.analysis)
        else:
            self._build_after_analysis.add(tab.doc_id)
            self.analyze(tab, immediate=True)

    def _start_build(self, tab: EditorTab, analysis: Analysis) -> None:
        assert analysis.program is not None
        tab.built_digest = analysis.digest
        self.builds.request(BuildRequest(tab.doc_id, analysis.program, tab.seed))

    def cancel_build(self) -> None:
        tab = self.tabs.current()
        if tab is not None:
            self.builds.cancel(tab.doc_id)

    @Slot(str)
    def on_build_started(self, doc_id: str) -> None:
        tab = self.tab(doc_id)
        if tab is not None:
            self.build_started.emit(tab)

    @Slot(str, object)
    def on_build_progress(self, doc_id: str, progress: object) -> None:
        tab = self.tab(doc_id)
        if tab is not None and isinstance(progress, BuildProgress):
            self.build_progress.emit(tab, progress)

    @Slot(str, object)
    def on_build_finished(self, doc_id: str, outcome: object) -> None:
        if not isinstance(outcome, BuildOutcome):
            return
        job = FunctionJob(f"preview {doc_id}", Lane.IO, _preview_job(doc_id, outcome), key=f"preview:{doc_id}")
        self.runner.submit(job).finished.connect(self.on_preview_ready)

    @Slot(object)
    def on_preview_ready(self, ready: object) -> None:
        if not isinstance(ready, PreviewReady):
            return
        tab = self.tab(ready.doc_id)
        if tab is None:
            return
        tab.outcome = ready.outcome
        camera, frame = None, False
        if not tab.camera_applied:  # first build: the script camera, or frame the structure
            view = settings_from_events(ready.outcome.scene.events)
            camera = view.view.camera() if view.has_view else None
            frame, tab.camera_applied = camera is None, True
        self.scene_ready.emit(tab, ready.outcome, ready.preview, camera, frame)

    @Slot(str, object)
    def on_build_failed(self, doc_id: str, info: object) -> None:
        message = info.message if isinstance(info, ErrorInfo) else str(info)
        log.error("build failed: %s", message)
        self.message.emit(f"Build failed: {message}")

    # -- seeds & parameters --------------------------------------------------------------------------------
    def set_seed(self, seed: int) -> None:
        tab = self.tabs.current()
        if tab is not None and tab.seed != seed:
            tab.seed = seed
            self.build(tab)

    def next_seed(self) -> int:
        tab = self.tabs.current()
        seed = ((tab.seed if tab else 0) + 1) % (MAX_SEED + 1)
        self.set_seed(seed)
        return seed

    def random_seed(self) -> int:
        seed = random.randint(0, MAX_SEED)
        self.set_seed(seed)
        return seed

    def set_parameter(self, name: str, value: float) -> None:
        tab = self.tabs.current()
        if tab is not None:
            tab.params[name] = value
            self._build_after_analysis.add(tab.doc_id)
            self.analyze(tab, immediate=True)


def _preview_job(doc_id: str, outcome: BuildOutcome) -> Any:
    def run(ctx: JobContext) -> PreviewReady:
        ctx.check_cancelled()
        return PreviewReady(doc_id, outcome, preview_scene(outcome.scene))

    return run
