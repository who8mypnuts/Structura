"""Report sections about the camera, the render settings, lighting, materials and performance."""

from __future__ import annotations

import math
from collections import Counter

import numpy as np

from ...core.scene.camera import Camera
from ...core.scene.lens import focal_length_mm
from ...core.scene.material import Material
from ...core.scene.vectors import fmt_vec as _vec
from ..details import RenderDetails
from ..progress import RenderProgress
from ..settings import RenderSettings
from .model import Row, Section, Table, row
from .system_sections import peak_memory


def _on(flag: bool) -> str:
    return "on" if flag else "off"


def _lens_rows(c: Camera) -> list[Row]:
    """The lens rows: the projection's own field, or the photographic lens and its depth of field."""
    lens = c.lens
    if lens.projection == "orthographic":
        return [row("Orthographic height", lens.ortho_height, f"{lens.ortho_height:g} world units")]
    if lens.projection == "fisheye":
        return [row("Fisheye field", lens.fisheye_fov_deg, f"{lens.fisheye_fov_deg:g}° ({lens.fisheye_mapping})")]
    if lens.projection != "perspective":
        return []
    sensor = f"{lens.sensor_mm[0]:g} × {lens.sensor_mm[1]:g} mm"
    rows = [row("Focal length", c.focal_length_mm, f"{c.focal_length_mm:.1f} mm on a {sensor} sensor"),
            row("Scene scale", lens.units_per_metre, f"{lens.units_per_metre:g} world units per metre")]  # fmt: skip
    if any(lens.shift):
        rows.append(row("Lens shift", list(lens.shift), _vec(lens.shift), "in frame heights"))
    if c.aperture_radius <= 0:
        return [*rows, row("Depth of field", False, "off (pinhole)")]
    near, far = c.sharp_range
    bokeh = f"{lens.blades} blades at {lens.blade_rotation_deg:g}°" if lens.blades >= 3 else "round"
    return [*rows,
        row("Aperture", c.fstop, f"f/{c.fstop:.3g} (radius {c.aperture_radius:.4g} world units)"),
        row("Focus distance", c.focus, f"{c.focus:.4g} ({lens.focus_mode})"),
        row("Sharp range", [near, far], f"{near:.4g} – {'∞' if math.isinf(far) else f'{far:.4g}'}",
            f"circle of confusion {lens.coc_mm:.3g} mm"),
        row("Bokeh", lens.blades, bokeh + (f", bias {lens.bokeh_bias:+g}" if lens.bokeh_bias else "")
            + (f", anamorphic {lens.anamorphic:g}" if lens.anamorphic != 1 else "")),
        *([row("Focus tilt", list(lens.tilt), f"{lens.tilt[0]:g}° / {lens.tilt[1]:g}°")] if any(lens.tilt) else []),
    ]  # fmt: skip


def camera_section(d: RenderDetails) -> Section:
    """Returns the report's camera section: position, direction, field of view and the lens.

    Args:
        d: What the render used.
    """
    c, s = d.camera, d.settings
    forward = c.basis[0]
    vertical = c.fov_y_deg
    horizontal = math.degrees(2 * math.atan(math.tan(math.radians(vertical) / 2) * s.aspect))
    yaw, pitch = math.degrees(math.atan2(forward[0], forward[2])), math.degrees(math.asin(float(forward[1])))
    rows: list[Row] = [
        row("Projection", c.lens.projection),
        row("Position", list(c.eye), _vec(c.eye)),
        row("Target", list(c.target), _vec(c.target)),
        row("Up", list(c.up), _vec(c.up)),
        row("View direction", forward.tolist(), _vec(forward)),
        row("Heading / pitch", [yaw, pitch], f"{yaw:.2f}° / {pitch:.2f}°", "rotation about +Y from +Z; elevation"),
        row("Distance to target", c.distance, f"{c.distance:.4g}"),
        row("Field of view (V × H)", [vertical, horizontal], f"{vertical:.2f}° × {horizontal:.2f}°"),
        row("Focal length (35 mm equivalent)", focal_length_mm(vertical), f"{focal_length_mm(vertical):.1f} mm"),
        row("Aspect ratio", s.aspect, f"{s.aspect:.4f} ({s.width} : {s.height})"),
        *_lens_rows(c),
    ]  # fmt: skip
    return Section("camera", "Camera", tuple(rows))


def _bounces(s: RenderSettings) -> str:
    limits = [(name, v) for name, v in (("diffuse", s.diffuse_bounces), ("glossy", s.glossy_bounces),
                                        ("transmission", s.transmission_bounces)) if v >= 0]  # fmt: skip
    return f"{s.max_bounces}" + (" (" + ", ".join(f"{n} {v}" for n, v in limits) + ")" if limits else "")


def settings_section(s: RenderSettings) -> Section:
    passes = "auto (time-paced)" if s.samples_per_pass <= 0 else f"{s.samples_per_pass}"
    rows = (
        row("Resolution", [s.width, s.height], f"{s.width} × {s.height} ({s.width * s.height / 1e6:.2f} MP)"),
        row("Integrator", s.integrator),
        row("Target samples per pixel", s.samples, f"{s.samples:,}"),
        row("Samples per pass", s.samples_per_pass, passes),
        row("Image sampler", s.sampler,
            f"tiled, {s.bucket_size} px buckets, {s.bucket_order} order" if s.sampler == "tiled" else "progressive"),
        row("Sample sequence", s.sequence),
        row("Max bounces", s.max_bounces, _bounces(s)),
        row("Sample clamp", s.clamp, f"{s.clamp:g}", "caps single-sample radiance to tame fireflies"),
        row("Pixel filter", s.filter),
        row("View transform", s.view_transform),
        row("Noise threshold", s.noise_threshold,
            f"{s.noise_threshold:g} (min {s.adaptive_min_samples} spp)" if s.noise_threshold > 0 else "off"),
        row("Time limit", s.time_limit, f"{s.time_limit:g} s" if s.time_limit > 0 else "none"),
        row("Caustics", s.caustics, s.caustics + (f" ({s.photon_count:,} photons)" if s.caustics == "photons" else "")),
        row("AOVs", s.aovs, _on(s.aovs), "albedo, normal, depth, alpha, ids"),
        row("Region", list(s.region) if s.region else None, _vec(s.region) if s.region else "full frame"),
        row("Random seed", s.seed),
    )  # fmt: skip
    return Section("settings", "Render settings", rows)


def lighting_section(d: RenderDetails) -> Section:
    """Returns the report's lighting section: environment, sun, lights (with a table of the declared ones).

    Args:
        d: What the render used.
    """
    s = d.settings
    env = {"gradient": f"gradient {_vec(s.sky_bottom)} → {_vec(s.sky_top)}",
           "hdri": f"HDRI {s.env_file or '(none)'}, rotated {s.env_rotation_deg:g}°",
           "sunsky": f"Preetham sun-sky, turbidity {s.turbidity:g}"}.get(s.env_type, s.env_type)  # fmt: skip
    lights = ", ".join(f"{n} {t}" for t, n in sorted(Counter(d.lights).items())) or "none"
    tables = (Table("Declared lights", ("Name", "Type", "Values"), d.light_specs),) if d.light_specs else ()
    rows = [
        row("Environment", s.env_type, env),
        row("Environment intensity", s.env_intensity, f"{s.env_intensity:g}"),
        row("Sun elevation / azimuth", [s.sun_elevation_deg, s.sun_azimuth_deg],
            f"{s.sun_elevation_deg:g}° / {s.sun_azimuth_deg:g}°"),
        row("Sun angular size", s.sun_angle_deg, f"{s.sun_angle_deg:g}°"),
        row("Sun irradiance", list(s.sun_irradiance), _vec(s.sun_irradiance)),
        row("Declared lights", list(d.lights), lights),
        row("Emissive primitives", d.emitters, f"{d.emitters:,}", "sampled directly by next-event estimation"),
        row("Shadows", s.shadows, _on(s.shadows)),
        row("Ground", s.ground_plane, s.ground_plane if s.ground_plane != "off" else "none"),
        row("Fog", s.fog_density, f"density {s.fog_density:g}, falloff {s.fog_falloff:g}" if s.fog_density else "none"),
    ]  # fmt: skip
    return Section("lighting", "Lighting & environment", tuple(rows), tables)


def _colour(value: str | tuple[float, float, float]) -> str:
    return "per object" if isinstance(value, str) else _vec(value)


def materials_section(materials: tuple[Material, ...]) -> Section:
    rows = tuple(
        (m.name, m.model.name.lower(), _colour(m.base), f"{m.metallic:g}", f"{m.roughness:g}", f"{m.ior:g}",
         f"{m.transmission:g}", f"{m.emission_strength:g}", f"{m.coat:g}")
        for m in materials
    )  # fmt: skip
    columns = ("Name", "Model", "Base colour", "Metallic", "Roughness", "IOR", "Transmission", "Emission", "Coat")
    summary = (row("Materials", len(materials), f"{len(materials):,}"),)
    return Section("materials", "Materials", summary, (Table("Material table", columns, rows),))


def _timing_rows(p: RenderProgress) -> list[Row]:
    """Kernel start-up and the spread of pass times."""
    rows = [row("Kernel start", p.kernel_seconds, f"{p.kernel_seconds:,.2f} s",
                "binding the render kernel: its first compile on a device, else uploading the scene")]  # fmt: skip
    if p.pass_seconds:
        times = np.asarray(p.pass_seconds)
        text = f"{times.min() * 1000:,.0f} / {times.mean() * 1000:,.0f} / {times.max() * 1000:,.0f} ms"
        rows.append(row("Pass time (min / mean / max)", [float(times.min()), float(times.mean()), float(times.max())],
                        text, "one pass (or bucket), including the read-back"))  # fmt: skip
    return rows


def performance_section(d: RenderDetails, p: RenderProgress, passes: int, device: str) -> Section:
    """Returns the report's performance section: times, throughput, BVH, device and memory.

    Args:
        d: What the render used.
        p: The final progress (samples, times).
        passes: How many passes the render took.
        device: The backend and device name ('cuda NVIDIA GeForce GTX 1660').
    """
    samples, seconds = p.samples, p.seconds
    pixels = d.settings.width * d.settings.height
    rate = samples * pixels / seconds if seconds > 0 else 0.0
    b = d.bvh
    peak = peak_memory()
    rows = (
        row("Device", device),
        *(row(f"Device: {label}", value) for label, value in d.device),
        row("Render time", seconds, f"{seconds:,.2f} s"),
        row("Scene preparation", d.prepare_seconds, f"{d.prepare_seconds:,.2f} s", "packing, BVH build, materials"),
        *_timing_rows(p),
        row("Samples reached", samples, f"{samples:,} spp"),
        row("Passes", passes, f"{passes:,}" + (f" (≈ {samples / passes:.1f} spp each)" if passes else "")),
        row("Throughput", rate, f"{rate / 1e6:,.2f} M samples/s", "pixel samples per second"),
        row("Samples per second per pixel", samples / seconds if seconds > 0 else 0.0,
            f"{samples / seconds:,.1f} spp/s" if seconds > 0 else "—"),
        row("Packed primitives", d.primitives, f"{d.primitives:,}"),
        row("Explicit triangles", d.triangles, f"{d.triangles:,}"),
        row("BVH nodes / leaves", [b.nodes, b.leaves], f"{b.nodes:,} / {b.leaves:,}"),
        row("BVH depth", b.depth),
        row("Primitives per leaf (mean / max)", [b.mean_leaf_size, b.max_leaf_size],
            f"{b.mean_leaf_size:.2f} / {b.max_leaf_size}"),
        row("BVH memory", b.bytes, f"{b.bytes / 2**20:.2f} MiB"),
        row("Scene radius", d.scene_radius, f"{d.scene_radius:.4g}"),
        row("Peak memory", peak, f"{peak / 2**20:,.0f} MiB" if peak else "—", "the process's largest resident size"),
    )  # fmt: skip
    return Section("performance", "Performance", rows)
