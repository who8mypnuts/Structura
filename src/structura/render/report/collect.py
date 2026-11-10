"""Gather everything known about a finished render into a Report (format-independent)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np

from ...core.build.driver import BuildStats
from ...core.scene.ir import SceneIR
from ..api import RenderProgress
from ..details import RenderDetails
from ..output import Display
from ..post import PostSettings
from . import image_stats as stats
from .model import Report, Row, Section, row
from .render_sections import camera_section, lighting_section, materials_section, performance_section, settings_section
from .scene_sections import build_section, geometry_section, script_section
from .system_sections import reproduce_section, system_section


@dataclass(frozen=True)
class ReportInputs:
    scene: SceneIR
    progress: RenderProgress
    details: RenderDetails
    device: str  # "cuda NVIDIA GeForce GTX 1660"
    passes: int = 0
    image: np.ndarray | None = None  # the image as saved (e.g. denoised); default: progress.image
    denoiser: str = ""
    display: Display | None = None  # exposure, view transform and post stack the image was saved with (None:
    # the render settings' own)
    script: str | None = None
    script_path: Path | None = None
    seed: int = 0
    params: dict[str, float] = field(default_factory=dict)
    build: BuildStats | None = None
    outputs: tuple[Path, ...] = ()  # files written alongside the report (the image)
    environment: dict[str, str] = field(default_factory=dict)  # extra system rows (Qt version, driver, …)


def _post_rows(post: PostSettings) -> list[Row]:
    """The post stack's non-default values (render/post.py)."""
    base = PostSettings()
    return [row(f"Post: {name.replace('_', ' ')}", value) for name, value in vars(post).items()
            if value != getattr(base, name)]  # fmt: skip


def _shown_with(inputs: ReportInputs) -> Display:
    return inputs.display or inputs.details.settings.display


def _image_section(inputs: ReportInputs, linear: np.ndarray, display: np.ndarray) -> Section:
    p, s, shown = inputs.progress, inputs.details.settings, _shown_with(inputs)
    rows: list[Row] = [
        row("Exposure", shown.exposure, f"{shown.exposure:+g} stops"),
        row("View transform", shown.view),
        *_post_rows(shown.post),
        row("Denoiser", inputs.denoiser or None, inputs.denoiser or "none"),
        *(row("Output file", str(path), path.name) for path in inputs.outputs),
        *stats.exposure_rows(linear, display),
        *stats.sampling_rows(p.sample_map, s.samples),
        *stats.visibility_rows(p.aovs, inputs.scene),
    ]  # fmt: skip
    return Section("image", "Image", tuple(rows))


def _image_with_camera(inputs: ReportInputs) -> Path | None:
    """A saved image (PNG or EXR carries the camera in its metadata) the reproduce command can take it from."""
    return next((p for p in inputs.outputs if p.suffix.lower() in (".png", ".exr")), None)


def _highlights(inputs: ReportInputs) -> tuple[tuple[str, str], ...]:
    s, p = inputs.details.settings, inputs.progress
    return (
        ("Resolution", f"{s.width} × {s.height}"),
        ("Objects", f"{len(inputs.scene):,}"),
        ("Samples", f"{p.samples:,} spp"),
        ("Render time", f"{p.seconds:,.1f} s"),
        ("Integrator", s.integrator),
        ("Device", inputs.device.split(" ")[0].upper() or "—"),
    )


def build_report(inputs: ReportInputs) -> Report:
    d, p = inputs.details, inputs.progress
    linear = inputs.image if inputs.image is not None else p.image
    display = _shown_with(inputs).apply(linear)
    name = inputs.script_path.name if inputs.script_path else "Untitled script"
    sections = [
        script_section(inputs.script, inputs.script_path, inputs.seed, inputs.params),
        geometry_section(inputs.scene),
        *([build_section(inputs.build)] if inputs.build is not None else []),
        camera_section(d),
        settings_section(d.settings),
        lighting_section(d),
        materials_section(d.materials),
        _image_section(inputs, linear, display),
        performance_section(d, p, inputs.passes, inputs.device),
        system_section(inputs.environment),
        reproduce_section(
            inputs.script_path, d.settings, inputs.seed, inputs.device, _image_with_camera(inputs), inputs.display
        ),
    ]
    created = datetime.now().astimezone().isoformat(timespec="seconds")
    return Report(
        title=f"Render report — {name}", subtitle=f"Structura · {created}", created=created,
        highlights=_highlights(inputs), sections=tuple(sections), thumbnail=stats.thumbnail(display),
        histogram=stats.histogram(display), palette=stats.palette(display),
    )  # fmt: skip
