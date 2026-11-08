"""Report sections about the camera, the render settings, lighting, materials and performance."""

from __future__ import annotations

import math

import numpy as np

from ...core.scene.material import STATE, Material
from ..details import RenderDetails
from ..settings import RenderSettings
from .model import Row, Section, Table, row

FULL_FRAME_HEIGHT_MM = 24.0  # 35 mm film: focal lengths are quoted for a 36 × 24 mm frame


def _vec(v: object) -> str:
    return "(" + ", ".join(f"{float(c):.4g}" for c in v) + ")"  # type: ignore[attr-defined]


def _on(flag: bool) -> str:
    return "on" if flag else "off"


def camera_section(d: RenderDetails) -> Section:
    c, s = d.camera, d.settings
    forward = c.basis[0]
    distance = float(np.linalg.norm(np.subtract(c.target, c.eye)))
    vertical = c.fov_y_deg
    horizontal = math.degrees(2 * math.atan(math.tan(math.radians(vertical) / 2) * s.aspect))
    focal = FULL_FRAME_HEIGHT_MM / (2 * math.tan(math.radians(vertical) / 2))
    yaw, pitch = math.degrees(math.atan2(forward[0], forward[2])), math.degrees(math.asin(float(forward[1])))
    rows: list[Row] = [
        row("Projection", s.camera_type),
        row("Position", list(c.eye), _vec(c.eye)),
        row("Target", list(c.target), _vec(c.target)),
        row("Up", list(c.up), _vec(c.up)),
        row("View direction", forward.tolist(), _vec(forward)),
        row("Heading / pitch", [yaw, pitch], f"{yaw:.2f}° / {pitch:.2f}°", "rotation about +Y from +Z; elevation"),
        row("Distance to target", distance, f"{distance:.4g}"),
        row("Field of view (V × H)", [vertical, horizontal], f"{vertical:.2f}° × {horizontal:.2f}°"),
        row("Focal length (35 mm equivalent)", focal, f"{focal:.1f} mm"),
        row("Aspect ratio", s.aspect, f"{s.aspect:.4f} ({s.width} : {s.height})"),
    ]  # fmt: skip
    if s.camera_type == "orthographic":
        rows.append(row("Orthographic height", s.ortho_height, f"{s.ortho_height:g} world units"))
    if s.camera_type == "fisheye":
        rows.append(row("Fisheye field", s.fisheye_fov, f"{s.fisheye_fov:g}°"))
    if c.aperture_radius > 0:
        rows += [
            row("Aperture radius", c.aperture_radius, f"{c.aperture_radius:.4g} world units"),
            row("Focus distance", c.focus, f"{c.focus:.4g}"),
            row("Bokeh", s.blades, f"{s.blades} blades at {s.blade_rotation_deg:g}°" if s.blades >= 3 else "round"),
        ]  # fmt: skip
    else:
        rows.append(row("Depth of field", False, "off (pinhole)"))
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
    s = d.settings
    env = {"gradient": f"gradient {_vec(s.sky_bottom)} → {_vec(s.sky_top)}",
           "hdri": f"HDRI {s.env_file or '(none)'}, rotated {s.env_rotation_deg:g}°",
           "sunsky": f"Preetham sun-sky, turbidity {s.turbidity:g}"}.get(s.env_type, s.env_type)  # fmt: skip
    lights = ", ".join(f"{n} {t}" for t, n in sorted(_count(d.lights).items())) or "none"
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
    return Section("lighting", "Lighting & environment", tuple(rows))


def _count(items: tuple[str, ...]) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in items:
        out[item] = out.get(item, 0) + 1
    return out


def _colour(value: str | tuple[float, float, float]) -> str:
    return "per object" if value == STATE else _vec(value)


def materials_section(materials: tuple[Material, ...]) -> Section:
    rows = tuple(
        (m.name, m.model.name.lower(), _colour(m.base), f"{m.metallic:g}", f"{m.roughness:g}", f"{m.ior:g}",
         f"{m.transmission:g}", f"{m.emission_strength:g}", f"{m.coat:g}")
        for m in materials
    )  # fmt: skip
    columns = ("Name", "Model", "Base colour", "Metallic", "Roughness", "IOR", "Transmission", "Emission", "Coat")
    summary = (row("Materials", len(materials), f"{len(materials):,}"),)
    return Section("materials", "Materials", summary, (Table("Material table", columns, rows),))


def performance_section(d: RenderDetails, samples: int, seconds: float, passes: int, device: str) -> Section:
    pixels = d.settings.width * d.settings.height
    rate = samples * pixels / seconds if seconds > 0 else 0.0
    b = d.bvh
    rows = (
        row("Device", device),
        row("Render time", seconds, f"{seconds:,.2f} s"),
        row("Scene preparation", d.prepare_seconds, f"{d.prepare_seconds:,.2f} s", "packing, BVH build, materials"),
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
    )  # fmt: skip
    return Section("performance", "Performance", rows)
