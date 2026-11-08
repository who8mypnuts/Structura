"""The render report's data model (docs/09 §11): every statistic, gathered once into a plain, serialisable
record so that every output format (Markdown, HTML, plain text, JSON, PDF) renders the same numbers.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np

from ... import __version__
from ...core.build.driver import BuildStats
from ...core.scene.camera import Camera
from ...core.scene.ir import PrimitiveKind, SceneIR
from ..api import Prepared
from ..settings import RenderSettings, render_param_specs

_LABELS = {spec.key: spec.title for spec in render_param_specs()}
# A few labels need to differ from the Render Settings panel's (docs/14 §3) to stay unambiguous next to a
# field of the same generic name, or a plain ParamSpec.title humanisation, in the report's full dump.
_LABELS |= {"ground": "Sky ground colour (sun-sky)", "camera_type": "Camera type"}


def _title(key: str) -> str:
    return _LABELS.get(key, key.replace("_", " ").capitalize())


def _value(raw: object) -> str:
    if isinstance(raw, bool):
        return "yes" if raw else "no"
    if isinstance(raw, float):
        return f"{raw:.6g}"
    if isinstance(raw, tuple):
        return ", ".join(_value(v) for v in raw)
    if raw is None or raw == "":
        return "—"
    return f"{raw:,}" if isinstance(raw, int) else str(raw)


def fields_table(obj: object) -> list[tuple[str, str]]:
    """Every field of a settings-like dataclass as (label, formatted value), in declaration order."""
    return [(_title(f.name), _value(getattr(obj, f.name))) for f in dataclasses.fields(obj)]  # type: ignore[arg-type]


def by_kind(scene: SceneIR) -> dict[str, int]:
    """Primitive counts by kind, largest first."""
    kinds, counts = np.unique(scene.kind, return_counts=True)
    pairs = sorted(zip(kinds.tolist(), counts.tolist(), strict=True), key=lambda p: -p[1])
    return {PrimitiveKind(int(k)).name.lower(): int(c) for k, c in pairs}


@dataclass(frozen=True)
class ScenePrepStats:
    """What the render-ready scene looks like, cheap to read off an already-built ``Prepared`` (render/api.py)."""

    render_primitives: int
    triangles: int
    bvh_nodes: int
    materials: int
    emitters: int
    bounds_lo: tuple[float, float, float]
    bounds_hi: tuple[float, float, float]


def prepared_stats(prepared: Prepared) -> ScenePrepStats:
    lo, hi = (float(v) for v in prepared.lo), (float(v) for v in prepared.hi)
    return ScenePrepStats(
        render_primitives=len(prepared.packed),
        triangles=int(prepared.packed.tri_f.shape[0]),
        bvh_nodes=prepared.bvh.nodes,
        materials=len(prepared.materials),
        emitters=len(prepared.emitters),
        bounds_lo=tuple(lo),  # type: ignore[arg-type]
        bounds_hi=tuple(hi),  # type: ignore[arg-type]
    )


@dataclass(frozen=True)
class ReportContext:
    """Everything ``build_report`` needs; the GUI fills it in from a finished ``RenderUpdate`` and the
    script's ``BuildOutcome``, the CLI from the same pieces it already has after ``render()``."""

    scene: SceneIR
    stats: BuildStats
    settings: RenderSettings
    build_seed: int
    camera: Camera | None = None
    scene_stats: ScenePrepStats | None = None
    device: str = ""
    achieved_samples: int = 0
    seconds: float = 0.0
    active: float = 1.0
    denoiser: str = ""
    script_name: str = ""
    script_sha256: str | None = None


@dataclass(frozen=True)
class ReportData:
    """Rendered to Markdown/HTML/text/JSON by ``render.report.text``; every field is already display-ready."""

    generated: str
    version: str
    script_name: str
    script_sha256: str | None
    build_seed: int
    render_seed: int
    objects: int
    by_kind: dict[str, int]
    build: list[tuple[str, str]]
    bounds_lo: tuple[float, float, float]
    bounds_hi: tuple[float, float, float]
    scene_stats: ScenePrepStats | None
    camera: list[tuple[str, str]] | None
    settings: list[tuple[str, str]]
    device: str
    achieved_samples: int
    target_samples: int
    seconds: float
    samples_per_second: float
    active: float
    denoiser: str
    width: int
    height: int


def build_report(ctx: ReportContext) -> ReportData:
    s = ctx.stats
    capped = " (maxobjects reached)" if s.objects >= s.max_objects else ""
    build = [
        ("Objects", f"{s.objects:,}{capped}"),
        ("Emitted", f"{s.emitted:,}"),
        ("Generations", f"{s.generations:,} (max {s.max_generations:,})"),
        ("Rule applications", f"{s.applications:,}"),
        ("Culled (max / min size)", f"{s.max_size_culled:,} / {s.min_size_culled:,}"),
        ("Traversal", "depth-first" if s.depth_first else "breadth-first"),
        ("Build time", f"{s.seconds * 1000:.1f} ms"),
    ]
    lo = ctx.scene_stats.bounds_lo if ctx.scene_stats else (0.0, 0.0, 0.0)
    hi = ctx.scene_stats.bounds_hi if ctx.scene_stats else (0.0, 0.0, 0.0)
    camera = fields_table(ctx.camera) if ctx.camera is not None else None
    return ReportData(
        generated=datetime.now(UTC).isoformat(timespec="seconds"),
        version=__version__,
        script_name=ctx.script_name,
        script_sha256=ctx.script_sha256,
        build_seed=ctx.build_seed,
        render_seed=ctx.settings.seed,
        objects=s.objects,
        by_kind=by_kind(ctx.scene),
        build=build,
        bounds_lo=lo,
        bounds_hi=hi,
        scene_stats=ctx.scene_stats,
        camera=camera,
        settings=fields_table(ctx.settings),
        device=ctx.device,
        achieved_samples=ctx.achieved_samples,
        target_samples=ctx.settings.samples,
        seconds=ctx.seconds,
        samples_per_second=ctx.achieved_samples / ctx.seconds if ctx.seconds > 0 else 0.0,
        active=ctx.active,
        denoiser=ctx.denoiser,
        width=ctx.settings.width,
        height=ctx.settings.height,
    )
