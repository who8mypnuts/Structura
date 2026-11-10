"""Workbench: connects documents, services and views (docs/02 §5). Holds no domain logic; it schedules.

Text edits → debounced analysis → (live mode) latest-wins build → preview upload on the io lane → viewport.
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, replace
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from ..core.lang.analysis import Analysis
from ..core.scene.camera import Camera
from ..core.scene.ir import SceneIR
from ..core.scene.material_look import material_look
from ..core.scene.settings import settings_from_events
from ..core.scene.view_filter import ViewFilter
from ..preview.instances import PreviewScene, preview_scene
from ..render.declarations import declared_camera
from ..services.build import (
    PREVIEW_OBJECTS,
    BuildLimits,
    BuildOutcome,
    BuildProgress,
    BuildRequest,
    BuildService,
    SceneCache,
)
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
    shown: SceneIR  # the scene as the viewport shows it (recoloured by the colour-by mode)
    recolor: bool = False  # only the colours changed (no new build)
    seconds: float = 0.0  # preparing the viewport scene (Build Stats)


class Workbench(QObject):
    analysis_shown = Signal(object, object)  # EditorTab, Analysis
    build_started = Signal(object)  # EditorTab
    build_progress = Signal(object, object)  # EditorTab, BuildProgress
    scene_ready = Signal(object, object, object, bool)  # tab, PreviewReady, Camera | None, frame
    recolored = Signal(object, object)  # tab, PreviewReady: the colour-by mode changed
    message = Signal(str)

    def __init__(self, tabs: DocumentTabs, runner: JobRunner) -> None:
        super().__init__(tabs)  # destroyed with the tabs: late results of closed windows go nowhere
        self.tabs, self.runner = tabs, runner
        self.language = LanguageService(runner)
        self.builds = BuildService(runner)
        self.live = True
        self.limits = BuildLimits()  # Build ▸ Build Limits…
        self.dragging = False  # a parameter slider is held: builds are capped at PREVIEW_OBJECTS
        self.cache = SceneCache()
        self.view = ViewFilter()  # colour-by, X-ray and isolation of the viewport (renders and exports: as built)
        self._build_after_analysis: set[str] = set()
        self._build_if_changed: set[str] = set()  # timeline frames: rebuild only when the program changed
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
        tl = tab.timeline
        req = AnalysisRequest(tab.doc_id, tab.text(), tab.version, tab.seed, params, script_dir, tab.frame, tl.fps)
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
            tab.editor.set_analysis(analysis)  # keep the last parsed symbols while the text has errors
        tab.editor.set_diagnostics(list(analysis.diagnostics))
        self.analysis_shown.emit(tab, analysis)
        wanted = doc_id in self._build_after_analysis
        changed = analysis.digest != tab.built_digest
        follow = doc_id in self._build_if_changed and changed
        self._build_after_analysis.discard(doc_id)
        self._build_if_changed.discard(doc_id)
        if analysis.ok and (wanted or follow or (self.live and changed)):
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
        limits = self.limits.capped(PREVIEW_OBJECTS) if self.dragging else self.limits
        cached = self.cache.get((analysis.digest, tab.seed, limits))
        if cached is not None:  # the same program, seed and limits were built a moment ago
            self.builds.cancel(tab.doc_id)
            self.on_build_finished(tab.doc_id, replace(cached, doc_id=tab.doc_id))
            return
        self.builds.request(BuildRequest(tab.doc_id, analysis.program, tab.seed, limits, analysis.digest))

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
        self.cache.put(outcome)
        if outcome.stopped and outcome.limits == self.limits:  # (capped drag previews are not news)
            count = f"{outcome.stats.objects:,}"
            self.message.emit(f"Build stopped at {count} objects: {outcome.stopped} (Build ▸ Build Limits…)")
        self.view = replace(self.view, isolate=None)  # an isolated set belongs to the previous build
        job = FunctionJob(f"preview {doc_id}", Lane.IO, _preview_job(doc_id, outcome, self.view),
                          key=f"preview:{doc_id}")  # fmt: skip
        self.runner.submit(job).finished.connect(self.on_preview_ready)

    @property
    def color_by(self) -> str:
        return self.view.color_by

    def set_color_by(self, mode: str) -> None:
        self.set_view(replace(self.view, color_by=mode))

    def set_view(self, view: ViewFilter) -> None:
        """Show the current scene through ``view`` (the preview is rebuilt on the io lane)."""
        self.view = view
        tab = self.tabs.current()
        if tab is not None and tab.outcome is not None:
            job = _preview_job(tab.doc_id, tab.outcome, view, recolor=True)
            handle = self.runner.submit(FunctionJob(f"colour {tab.doc_id}", Lane.IO, job, key=f"preview:{tab.doc_id}"))
            handle.finished.connect(self.on_preview_ready)

    @Slot(object)
    def on_preview_ready(self, ready: object) -> None:
        if not isinstance(ready, PreviewReady):
            return
        tab = self.tab(ready.doc_id)
        if tab is None:
            return
        if ready.recolor:
            if tab.outcome is ready.outcome:  # not superseded by a newer build
                self.recolored.emit(tab, ready)
            return
        tab.outcome = ready.outcome
        camera, frame = None, False
        if tab.camera_locked:  # Lock to Script: the script's camera after every build
            camera = script_camera(ready.outcome.scene)
        elif not tab.camera_applied:  # first build: a project's camera, the script camera, or frame the structure
            camera = tab.initial_camera or script_camera(ready.outcome.scene)
            frame, tab.camera_applied = camera is None, True
        self.scene_ready.emit(tab, ready, camera, frame)

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

    def finish_drag(self) -> None:
        """The slider was released: the full build replaces the capped preview."""
        if self.dragging:
            self.dragging = False
            self.build()

    def follow_frame(self, tab: EditorTab) -> None:
        """The timeline moved: re-analyse now and rebuild if the program changed (even without live mode)."""
        self._build_if_changed.add(tab.doc_id)
        self.analyze(tab, immediate=True)

    def set_parameter(self, name: str, value: float, dragging: bool = False) -> None:
        self.set_parameters({name: value}, dragging)

    def set_parameters(self, values: dict[str, float], dragging: bool = False) -> None:
        """New parameter values: rebuild (capped at PREVIEW_OBJECTS while a slider is dragged)."""
        self.dragging = dragging
        tab = self.tabs.current()
        if tab is not None:
            tab.params.update(values)
            self._build_after_analysis.add(tab.doc_id)
            self.analyze(tab, immediate=True)


def script_camera(scene: SceneIR) -> Camera | None:
    """The camera the script sets (a v2 camera block, or 'set translation/rotation/…'), or None."""
    view = settings_from_events(scene.events)
    legacy = view.view.camera() if view.has_view else None
    return declared_camera(scene.declarations, legacy or view.view.camera()) or legacy


def _preview_job(doc_id: str, outcome: BuildOutcome, view: ViewFilter, recolor: bool = False) -> Any:
    def run(ctx: JobContext) -> PreviewReady:
        ctx.check_cancelled()
        started = time.perf_counter()
        shown = view.apply(outcome.scene)
        looks = material_look(outcome.scene) if view.color_by == "authored" else outcome.scene
        preview = preview_scene(shown if looks is outcome.scene else view.apply(looks))  # GL: materials approximated
        return PreviewReady(doc_id, outcome, preview, shown, recolor, time.perf_counter() - started)

    return run
