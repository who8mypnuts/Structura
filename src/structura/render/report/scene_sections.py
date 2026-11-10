"""Report sections about the script, the generated structure and its build."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from ...core.build.driver import BuildStats
from ...core.geometry.unit_shapes import unit_box, unit_cylinder, unit_sphere, unit_torus
from ...core.scene.ir import PrimitiveKind, SceneIR
from ...core.scene.vectors import fmt_vec
from ..pack import box_bounds
from .model import Row, Section, Table, row

K = PrimitiveKind


def _triangles_per_instance() -> dict[PrimitiveKind, int]:
    sphere, cylinder = unit_sphere().triangles, unit_cylinder().triangles
    return {K.BOX: unit_box().triangles, K.SPHERE: sphere, K.ELLIPSOID: sphere, K.CYLINDER: cylinder,
            K.CONE: cylinder, K.TORUS: unit_torus().triangles, K.TRIANGLE: 1, K.GRID: 12 * 12}  # fmt: skip


def _vec(v: np.ndarray) -> str:
    return fmt_vec(v, ".3f")


def script_section(text: str | None, path: Path | None, seed: int, params: dict[str, float]) -> Section:
    rows: list[Row] = [row("File", str(path) if path else "unsaved", path.name if path else "(unsaved script)")]
    if text is not None:
        lines = text.splitlines()
        code = [ln for ln in lines if ln.strip() and not ln.strip().startswith("//")]
        rules = sum(1 for ln in code if ln.lstrip().lower().startswith("rule "))
        rows += [
            row("Dialect", "v2" if text.lstrip().startswith("#version 2") else "v1",
                "EisenScript v2" if text.lstrip().startswith("#version 2") else "EisenScript v1 (Structure Synth 1.5)"),
            row("Lines", len(lines), f"{len(lines):,} ({len(code):,} code, {len(lines) - len(code):,} other)",
                "other: blank lines and comments"),
            row("Characters", len(text), f"{len(text):,}"),
            row("Rule definitions", rules, f"{rules:,}", "'rule' lines, counting ambiguous alternatives"),
            row("SHA-256", hashlib.sha256(text.encode("utf-8")).hexdigest(), note="identifies the exact script text"),
        ]  # fmt: skip
    rows.append(row("Seed", seed, f"{seed:,}"))
    rows += [row(f"Parameter {name}", value, f"{value:g}") for name, value in sorted(params.items())]
    return Section("script", "Script", tuple(rows))


def _bounds_rows(scene: SceneIR, drawn: np.ndarray) -> list[Row]:
    lo, hi = box_bounds(scene.xform[drawn])
    lo, hi = lo.min(axis=0).astype(np.float64), hi.max(axis=0).astype(np.float64)
    size = hi - lo
    volume = float(np.prod(np.maximum(size, 1e-9)))
    return [
        row("Bounding box min", lo.tolist(), _vec(lo)),
        row("Bounding box max", hi.tolist(), _vec(hi)),
        row("Extent (W × H × D)", size.tolist(), " × ".join(f"{s:.3f}" for s in size)),
        row("Centre", ((lo + hi) / 2).tolist(), _vec((lo + hi) / 2)),
        row("Diagonal", float(np.linalg.norm(size)), f"{np.linalg.norm(size):.3f}"),
        row("Density", int(drawn.sum()) / volume, f"{int(drawn.sum()) / volume:,.2f} objects per unit³",
            "objects per bounding-box volume"),
    ]  # fmt: skip


def _instance_rows(scene: SceneIR, drawn: np.ndarray) -> list[Row]:
    linear = scene.xform[drawn][:, :, :3].astype(np.float64)
    sizes = np.linalg.norm(linear, axis=1).max(axis=1)
    det = np.linalg.det(linear)
    unit = linear / np.maximum(np.linalg.norm(linear, axis=1, keepdims=True), 1e-12)
    gram = np.einsum("nij,nik->njk", unit, unit) - np.eye(3)
    sheared = int((np.abs(gram).max(axis=(1, 2)) > 1e-4).sum())
    smallest, largest = float(sizes.min()), float(sizes.max())
    colours = int(np.unique(scene.rgba[drawn].round(4), axis=0).shape[0])
    transparent = int((scene.rgba[drawn, 3] < 1).sum())
    return [
        row("Instance size (min / median / max)", [smallest, float(np.median(sizes)), largest],
            f"{smallest:.4g} / {np.median(sizes):.4g} / {largest:.4g}", "longest axis of each instance frame"),
        row("Scale range", largest / max(smallest, 1e-30), f"{largest / max(smallest, 1e-30):,.1f} : 1"),
        row("Mirrored instances", int((det < 0).sum()), f"{int((det < 0).sum()):,}", "negative determinant"),
        row("Sheared instances", sheared, f"{sheared:,}", "non-orthogonal frames: exports bake them or use matrices"),
        row("Transparent instances", transparent, f"{transparent:,}"),
        row("Distinct colours", colours, f"{colours:,}"),
        row("Tags", list(scene.tags), ", ".join(t for t in scene.tags if t) or "—"),
    ]  # fmt: skip


def _scene_bytes(scene: SceneIR) -> int:
    return sum(int(getattr(scene, n).nbytes) for n in ("kind", "xform", "rgba", "tag", "source", "generation", "aux",
                                                        "aux_data"))  # fmt: skip


def geometry_section(scene: SceneIR) -> Section:
    drawn = scene.kind != K.TEMPLATE
    counts = scene.kind_counts()
    total = max(1, len(scene))
    per = {kind.name.lower(): n for kind, n in _triangles_per_instance().items()}
    kinds = tuple(
        (kind, f"{count:,}", f"{100 * count / total:.1f} %", f"{count * per[kind]:,}" if kind in per else "—")
        for kind, count in counts.items()
    )
    estimate = sum(c * per.get(k, 0) for k, c in counts.items())
    rows = [
        row("Objects", len(scene), f"{len(scene):,}"),
        row("Primitive kinds", len(counts), f"{len(counts)}"),
        row("Triangles if baked", estimate, f"≈ {estimate:,}", "mesh export with the default tessellation"),
        row("Generations", int(scene.generation.max(initial=0)), f"{int(scene.generation.max(initial=0)):,}",
            "deepest recursion level that emitted an object"),
        row("Scene memory", _scene_bytes(scene), f"{_scene_bytes(scene) / 2**20:.2f} MiB", "the SceneIR arrays"),
    ]  # fmt: skip
    if drawn.any():
        rows += _bounds_rows(scene, drawn) + _instance_rows(scene, drawn)
    table = Table("Objects by kind", ("Kind", "Count", "Share", "Triangles if baked"), kinds)
    return Section("geometry", "Geometry", tuple(rows), (table,))


def build_section(stats: BuildStats) -> Section:
    rate = stats.objects / stats.seconds if stats.seconds > 0 else 0.0
    capped = stats.objects >= stats.max_objects
    rows = (
        row("Build time", stats.seconds, f"{stats.seconds * 1000:,.1f} ms"),
        row("Throughput", rate, f"{rate:,.0f} objects/s"),
        row("Objects emitted", stats.emitted, f"{stats.emitted:,}"),
        row("Rule applications", stats.applications, f"{stats.applications:,}"),
        row("Generations", stats.generations, f"{stats.generations:,} of max {stats.max_generations:,}",
            "'set maxdepth'"),
        row("Object limit", stats.max_objects, f"{stats.max_objects:,}" + (" — reached" if capped else ""),
            "'set maxobjects'"),
        row("Culled by size (max / min)", [stats.max_size_culled, stats.min_size_culled],
            f"{stats.max_size_culled:,} / {stats.min_size_culled:,}", "'set maxsize' / 'set minsize'"),
        row("Traversal", "depth-first" if stats.depth_first else "breadth-first",
            "depth-first" if stats.depth_first else "breadth-first (Structure Synth default)"),
    )  # fmt: skip
    return Section("build", "Build", rows)
