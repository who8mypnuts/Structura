"""Language, build and render services end to end on real lanes (docs/04)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from PySide6.QtCore import QObject, Slot
from pytestqt.qtbot import QtBot

from structura.core.build.api import build_scene
from structura.core.lang.analysis import Analysis, analyze
from structura.render.settings import RenderSettings
from structura.services.build import BuildOutcome, BuildRequest, BuildService
from structura.services.jobs import JobRunner
from structura.services.language import LanguageService
from structura.services.language.service import AnalysisRequest
from structura.services.render import RenderRequest, RenderService, RenderUpdate


class Sink(QObject):
    def __init__(self) -> None:
        super().__init__()
        self.items: list[tuple[str, Any]] = []

    @Slot(str, object)
    def take(self, doc: str, value: object) -> None:
        self.items.append((doc, value))


@pytest.fixture
def runner() -> Iterator[JobRunner]:
    r = JobRunner()
    yield r
    r.shutdown()


def test_analysis_is_debounced_and_reports_errors(qtbot: QtBot, runner: JobRunner) -> None:
    service, sink = LanguageService(runner, debounce_ms=30), Sink()
    service.analysis_ready.connect(sink.take)
    for version, text in enumerate(["rule R {", "rule R { box }\nR", "rule R { box }\nR\nQ"]):
        service.request(AnalysisRequest("doc", text, version))
    qtbot.waitUntil(lambda: bool(sink.items), timeout=5000)
    qtbot.wait(100)
    assert len(sink.items) == 1  # three edits, one analysis
    analysis = sink.items[0][1]
    assert isinstance(analysis, Analysis) and analysis.version == 2 and not analysis.ok
    assert analysis.diagnostics[-1].code == "E003"


def test_build_then_render(qtbot: QtBot, runner: JobRunner) -> None:
    builds, renders, sink = BuildService(runner), RenderService(runner), Sink()
    builds.finished.connect(sink.take)
    renders.finished.connect(sink.take)
    program = analyze("set maxdepth 6\nR\nrule R { { x 1 rz 30 s 0.9 } R box }").program
    assert program is not None
    builds.request(BuildRequest("doc", program, seed=3))
    qtbot.waitUntil(lambda: len(sink.items) == 1, timeout=20000)
    outcome = sink.items[0][1]
    assert isinstance(outcome, BuildOutcome)
    assert len(outcome.scene) == len(build_scene(program, 3).scene) > 0  # same result as the direct API
    settings = RenderSettings(width=24, height=16, samples=2, samples_per_pass=1, integrator="preview", frame=True)
    renders.request(RenderRequest("doc", outcome.scene, settings, device="cpu"))
    qtbot.waitUntil(lambda: len(sink.items) == 2, timeout=60000)
    update = sink.items[1][1]
    assert isinstance(update, RenderUpdate) and update.progress.samples == 2 and update.fraction == 1.0
    assert update.progress.image.shape == (16, 24, 3)


def test_render_with_denoise_finishes_with_the_denoised_image(qtbot: QtBot, runner: JobRunner) -> None:
    renders, sink = RenderService(runner), Sink()
    renders.finished.connect(sink.take)
    scene = build_scene(analyze("sphere").program).scene  # type: ignore[arg-type]
    settings = RenderSettings(width=16, height=12, samples=2, samples_per_pass=2, frame=True, aovs=True)
    renders.request(RenderRequest("doc", scene, settings, device="cpu", denoise="atrous"))
    qtbot.waitUntil(lambda: len(sink.items) == 1, timeout=60000)
    update = sink.items[0][1]
    assert isinstance(update, RenderUpdate) and update.denoiser == "atrous"
    assert update.denoised is not None and update.denoised.shape == (12, 16, 3)
