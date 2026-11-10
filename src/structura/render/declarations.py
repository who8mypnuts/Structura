"""EisenScript v2 blocks → render settings and camera (docs/05 §9.4–9.5). 'camera' and 'render' blocks
override the legacy 'set' equivalents (W113); the first sun light and the environment drive the sky."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np

from ..core.color import linear_of, rgb_of
from ..core.scene.camera import Camera
from ..core.scene.camera_block import camera_from_block
from ..core.scene.declarations import SceneDeclarations
from ..core.scene.vectors import vec3_of
from .ground import MODES as GROUND_MODES
from .post import post_from_block
from .settings import (
    BUCKET_ORDERS,
    DENOISERS,
    FILTER_NAMES,
    INTEGRATORS,
    SAMPLERS,
    SEQUENCES,
    SKY_BOTTOM,
    SKY_GROUND,
    SKY_TOP,
    VIEWS,
    RenderSettings,
)

CHOICES: dict[str, tuple[str, tuple[str, ...]]] = {  # block key → (settings field, allowed values)
    "integrator": ("integrator", tuple(INTEGRATORS)),
    "filter": ("filter", FILTER_NAMES),
    "caustics": ("caustics", ("filtered", "on", "photons")),
    "sampler": ("sampler", SAMPLERS),
    "bucket_order": ("bucket_order", BUCKET_ORDERS),
    "sequence": ("sequence", SEQUENCES),
    "view": ("view", VIEWS),
    "denoise": ("denoise", DENOISERS),
}
INTS = {"samples": ("samples", 1), "max_bounces": ("max_bounces", 0),
        "photon_count": ("photon_count", 1000), "bucket_size": ("bucket_size", 8),
        "diffuse_bounces": ("diffuse_bounces", 0), "glossy_bounces": ("glossy_bounces", 0),
        "transmission_bounces": ("transmission_bounces", 0)}  # block key → (field, minimum)  # fmt: skip
TRUE = ("true", "on", "yes", "1")
FLOATS = {"noise_threshold": "noise_threshold", "time_limit": "time_limit", "photon_radius": "photon_radius",
          "exposure": "exposure"}  # fmt: skip


def _render_block(block: dict[str, Any]) -> dict[str, Any]:
    """Render settings from the render block's keys (choices, counts, numbers, the look and the size)."""
    out: dict[str, Any] = {field: str(block[key]) for key, (field, allowed) in CHOICES.items()
                           if str(block.get(key, "")) in allowed}  # fmt: skip
    out |= {field: max(low, int(block[key])) for key, (field, low) in INTS.items() if key in block}
    out |= {field: float(block[key]) for key, field in FLOATS.items() if key in block}
    for key in ("noise_threshold", "time_limit", "photon_radius"):
        if key in out:
            out[key] = max(0.0, out[key])
    if "ao_direct" in block:
        out["ao_direct"] = str(block["ao_direct"]).lower() in TRUE
    if (post := post_from_block(block)) is not None:
        out["post"] = post
    size = str(block.get("size", ""))
    if "x" in size:  # (block_check let only digits 'x' digits through)
        w, _, h = size.lower().partition("x")
        out["width"], out["height"] = max(1, int(w)), max(1, int(h))
    return out


def _ground(block: dict[str, Any]) -> dict[str, Any]:
    """Ground and fog keys of the render block."""
    out: dict[str, Any] = {k: float(block[k]) for k in ("fog_density", "fog_falloff", "fog_base", "ground_offset")
                           if k in block}  # fmt: skip
    if str(block.get("ground", "")) in GROUND_MODES:
        out["ground_plane"] = str(block["ground"])
    for key in ("fog_color", "ground_color"):
        if key in block and (colour := rgb_of(block[key])) is not None:
            out[key] = colour
    return out


def _sun(decl: SceneDeclarations) -> dict[str, Any]:
    """The sun: the light 'environment { sun NAME }' names, else the first sun light."""
    suns = [light for light in decl.lights if light.type == "sun"]
    named = str(decl.environment.get("sun", "")).lower()
    sun = next((light for light in suns if light.name.lower() == named), suns[0] if suns else None)
    if sun is None:  # a script that declares its lighting has no implicit sun (night scenes, studio lights)
        return {"sun_irradiance": (0.0, 0.0, 0.0)} if decl.lights or decl.environment else {}
    out: dict[str, Any] = {}
    travel = vec3_of(sun.values.get("direction"))
    if travel is not None:
        d = -np.asarray(travel) / (np.linalg.norm(travel) or 1.0)  # towards the sun
        out["sun_vector"] = (float(d[0]), float(d[1]), float(d[2]))
    colour = linear_of(sun.values.get("color"), (1.0, 1.0, 1.0))
    intensity = float(sun.values.get("intensity", 3.0))
    out["sun_irradiance"] = (colour[0] * intensity, colour[1] * intensity, colour[2] * intensity)
    if "angle" in sun.values:
        out["sun_angle_deg"] = float(sun.values["angle"])
    return out


def _environment(block: dict[str, Any]) -> dict[str, Any]:
    """Render settings from the environment block: an HDRI, the sun-sky, a colour or a gradient."""
    kind = str(block.get("type", ""))
    shared = {k: float(block[key]) for key, k in (("rotation", "env_rotation_deg"), ("intensity", "env_intensity"))
              if key in block}  # fmt: skip
    if kind == "hdri":
        return {"env_type": "hdri", "env_file": str(block.get("file", "")), **shared}
    if kind == "sunsky":
        ground = {"ground": linear_of(block["ground"], SKY_GROUND)} if "ground" in block else {}
        turbidity = {"turbidity": float(block["turbidity"])} if "turbidity" in block else {}
        return {"env_type": "sunsky", **turbidity, **ground, **shared}
    if kind == "color":
        c = linear_of(block.get("color"), (1.0, 1.0, 1.0))
        return {"sky_top": c, "sky_bottom": c}
    if kind == "gradient":
        return {
            "sky_top": linear_of(block.get("top"), SKY_TOP),
            "sky_bottom": linear_of(block.get("bottom"), SKY_BOTTOM),
        }
    return {}


def declared_settings(
    settings: RenderSettings, decl: SceneDeclarations | None, has_background: bool = False
) -> RenderSettings:
    """Applies a script's v2 blocks to render settings.

    Args:
        settings: The settings so far (defaults and legacy 'set raytracer::' values).
        decl: The script's declarations; None (a v1 script) changes nothing.
        has_background: Whether the script sets a background colour (then camera rays keep seeing it).

    Returns:
        The settings with the render, environment and sun blocks applied.
    """
    if decl is None:
        return settings
    values = {
        **_render_block(decl.render),
        **_ground(decl.render),
        **_sun(decl),
        **_environment(decl.environment),
    }
    if decl.environment and not has_background:
        values["backdrop_sky"] = True
    return replace(settings, **values)


def declared_camera(decl: SceneDeclarations | None, fallback: Camera) -> Camera | None:
    """Reads the script's camera block.

    Args:
        decl: The script's declarations, if any.
        fallback: The camera that supplies what the block leaves out.

    Returns:
        The camera, or None when the script has no camera block.
    """
    if decl is None or not decl.camera:
        return None
    return camera_from_block(decl.camera, fallback)
