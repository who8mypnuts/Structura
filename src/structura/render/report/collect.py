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
from ..output import to_display
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
    exposure: float = 0.0
    view: str = ""  # the view transform the image was saved with ("": the settings' view)
    script: str | None = None
    script_path: Path | None = None
    seed: int = 0
    params: dict[str, float] = field(default_factory=dict)
    build: BuildStats | None = None
    outputs: tuple[Path, ...] = ()  # files written alongside the report (the image)
    environment: dict[str, str] = field(default_factory=dict)  # extra system rows (Qt version, driver, …)


def _image_section(inputs: ReportInputs, linear: np.ndarray, display: np.ndarray) -> Section:
    p, s = inputs.progress, inputs.details.settings
    rows: list[Row] = [
        row("Exposure", inputs.exposure, f"{inputs.exposure:+g} stops"),
        row("View transform", inputs.view or inputs.details.settings.view_transform),
        row("Denoiser", inputs.denoiser or None, inputs.denoiser or "none"),
        *(row("Output file", str(path), path.name) for path in inputs.outputs),
        *stats.exposure_rows(linear, display),
        *stats.sampling_rows(p.sample_map, s.samples),
        *stats.visibility_rows(p.aovs, inputs.scene),
    ]  # fmt: skip
    return Section("image", "Image", tuple(rows))


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
    display = to_display(linear, inputs.exposure, inputs.view or d.settings.view_transform)
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
        performance_section(d, p.samples, p.seconds, inputs.passes, inputs.device),
        system_section(inputs.environment),
        reproduce_section(inputs.script_path, d.settings, inputs.seed, inputs.device),
    ]
    created = datetime.now().astimezone().isoformat(timespec="seconds")
    return Report(
        title=f"Render report — {name}", subtitle=f"Structura · {created}", created=created,
        highlights=_highlights(inputs), sections=tuple(sections), thumbnail=stats.thumbnail(display),
        histogram=stats.histogram(display), palette=stats.palette(display),
    )  # fmt: skip
