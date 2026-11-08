"""Build limits (docs/06 §10.2, docs/14 §4.1): object and time caps and the memory guard stop a build early
with what it made so far; the stop reason travels with the outcome."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from structura.core.lang.api import compile_script
from structura.core.lang.compile.program import RuleProgram
from structura.services import build as build_module
from structura.services.build import BuildLimits, BuildRequest, build_job
from structura.services.jobs.job import JobContext

BIG = "set maxobjects 1000000\nset maxdepth 15\nR\nrule R { { x 1 } R { y 1 } R box }\n"


def _program() -> RuleProgram:
    program = compile_script(BIG, 1).program
    assert program is not None
    return program


def _run(limits: BuildLimits):  # type: ignore[no-untyped-def]
    return build_job(BuildRequest("doc", _program(), 1, limits))(JobContext(lambda *_: None, lambda *_: None))


def test_no_limits_means_the_script_decides() -> None:
    outcome = _run(BuildLimits())
    assert outcome.stopped == "" and outcome.stats.objects > 0


def test_the_object_limit_stops_the_build_with_what_it_has() -> None:
    outcome = _run(BuildLimits(max_objects=500))
    assert "object limit" in outcome.stopped and 500 <= len(outcome.scene) < 100_000


def test_the_memory_guard_stops_before_the_buffers_outgrow_the_share(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(build_module.psutil, "virtual_memory", lambda: SimpleNamespace(available=4_000_000))
    outcome = _run(BuildLimits(memory_percent=10))
    assert "memory guard" in outcome.stopped


def test_capping_for_drag_previews_keeps_the_smaller_limit() -> None:
    assert BuildLimits().capped(250_000).max_objects == 250_000
    assert BuildLimits(max_objects=1000).capped(250_000).max_objects == 1000


def test_the_scene_cache_keeps_recent_finished_builds_within_bounds() -> None:
    from structura.services.build import SceneCache  # noqa: PLC0415

    cache = SceneCache(entries=2, objects=10_000)
    outcomes = [replace(_run(BuildLimits(max_objects=0)), digest=f"d{i}", seed=i) for i in range(3)]
    for outcome in outcomes:
        cache.put(outcome)
    assert cache.get(("d0", 0, BuildLimits())) is None  # the oldest went first
    assert cache.get(("d2", 2, BuildLimits())) is outcomes[2]
    cache.put(replace(outcomes[0], digest="stopped", stopped="the object limit"))
    assert cache.get(("stopped", 0, BuildLimits())) is None  # partial builds are never reused
