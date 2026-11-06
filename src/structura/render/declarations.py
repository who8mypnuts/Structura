"""EisenScript v2 blocks → render settings and camera (docs/05 §9.4–9.5). 'camera' and 'render' blocks
override the legacy 'set' equivalents (W113); the first sun light and the environment drive the sky."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np

from ..core.color import parse_color, srgb_to_linear
from ..core.scene.camera import Camera
from ..core.scene.declarations import SceneDeclarations
from .ground import MODES as GROUND_MODES
from .settings import FILTER_NAMES, INTEGRATORS, RenderSettings

RGB = tuple[float, float, float]


def _linear(value: Any, default: RGB) -> RGB:
    c = parse_color(str(value)) if value is not None else None
    if c is None:
        return default
    r, g, b = (float(v) for v in srgb_to_linear(np.array([c.r, c.g, c.b], np.float32) / np.float32(65535)))
    return (r, g, b)


def _vec(value: Any) -> RGB | None:
    return (float(value[0]), float(value[1]), float(value[2])) if isinstance(value, tuple) and len(value) == 3 else None


CHOICES: dict[str, tuple[str, tuple[str, ...]]] = {  # block key → (settings field, allowed values)
    "integrator": ("integrator", tuple(INTEGRATORS)),
    "type": ("camera_type", ("perspective", "orthographic", "spherical", "fisheye")),
    "filter": ("filter", FILTER_NAMES),
    "caustics": ("caustics", ("filtered", "on", "photons")),
}
INTS = {"samples": ("samples", 1), "max_bounces": ("max_bounces", 0), "blades": ("blades", 0),
        "photon_count": ("photon_count", 1000)}  # block key → (field, minimum)  # fmt: skip
FLOATS = {"height": "ortho_height", "blade_rotation": "blade_rotation_deg", "noise_threshold": "noise_threshold",
          "time_limit": "time_limit", "photon_radius": "photon_radius"}  # fmt: skip


def _render_block(block: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {field: str(block[key]) for key, (field, allowed) in CHOICES.items()
                           if str(block.get(key, "")) in allowed}  # fmt: skip
    out |= {field: max(low, int(block[key])) for key, (field, low) in INTS.items() if key in block}
    out |= {field: float(block[key]) for key, field in FLOATS.items() if key in block}
    for key in ("noise_threshold", "time_limit", "photon_radius"):
        if key in out:
            out[key] = max(0.0, out[key])
    size = str(block.get("size", ""))
    if "x" in size:
        w, _, h = size.lower().partition("x")
        out["width"], out["height"] = int(w), int(h)
    return out


def _srgb(block: dict[str, Any], key: str) -> RGB | None:
    c = parse_color(str(block[key])) if key in block else None
    return None if c is None else (c.r / 65535, c.g / 65535, c.b / 65535)


def _ground(block: dict[str, Any]) -> dict[str, Any]:
    """Ground and fog keys of the render block."""
    out: dict[str, Any] = {k: float(block[k]) for k in ("fog_density", "fog_falloff", "fog_base", "ground_offset")
                           if k in block}  # fmt: skip
    if str(block.get("ground", "")) in GROUND_MODES:
        out["ground_plane"] = str(block["ground"])
    for key in ("fog_color", "ground_color"):
        if (colour := _srgb(block, key)) is not None:
            out[key] = colour
    return out


def _sun(decl: SceneDeclarations) -> dict[str, Any]:
    sun = next((light for light in decl.lights if light.type == "sun"), None)
    if sun is None:  # a script that declares its lighting has no implicit sun (night scenes, studio lights)
        return {"sun_irradiance": (0.0, 0.0, 0.0)} if decl.lights or decl.environment else {}
    out: dict[str, Any] = {}
    travel = _vec(sun.values.get("direction"))
    if travel is not None:
        d = -np.asarray(travel) / (np.linalg.norm(travel) or 1.0)  # towards the sun
        out["sun_vector"] = (float(d[0]), float(d[1]), float(d[2]))
    colour = _linear(sun.values.get("color"), (1.0, 1.0, 1.0))
    intensity = float(sun.values.get("intensity", 3.0))
    out["sun_irradiance"] = (colour[0] * intensity, colour[1] * intensity, colour[2] * intensity)
    if "angle" in sun.values:
        out["sun_angle_deg"] = float(sun.values["angle"])
    return out


def _environment(block: dict[str, Any]) -> dict[str, Any]:
    kind = str(block.get("type", ""))
    shared = {k: float(block[key]) for key, k in (("rotation", "env_rotation_deg"), ("intensity", "env_intensity"))
              if key in block}  # fmt: skip
    if kind == "hdri":
        return {"env_type": "hdri", "env_file": str(block.get("file", "")), **shared}
    if kind == "sunsky":
        ground = {"ground": _linear(block["ground"], (0.06, 0.055, 0.05))} if "ground" in block else {}
        turbidity = {"turbidity": float(block["turbidity"])} if "turbidity" in block else {}
        return {"env_type": "sunsky", **turbidity, **ground, **shared}
    if kind == "color":
        c = _linear(block.get("color"), (1.0, 1.0, 1.0))
        return {"sky_top": c, "sky_bottom": c}
    if kind == "gradient":
        return {"sky_top": _linear(block.get("top"), (0.55, 0.65, 0.85)),
                "sky_bottom": _linear(block.get("bottom"), (0.25, 0.24, 0.22))}  # fmt: skip
    return {}


def declared_settings(
    settings: RenderSettings, decl: SceneDeclarations | None, has_background: bool = False
) -> RenderSettings:
    if decl is None:
        return settings
    camera = {k: v for k, v in _render_block(decl.camera).items()
              if k in ("camera_type", "ortho_height", "blades", "blade_rotation_deg")}  # fmt: skip
    if decl.camera.get("type") == "fisheye" and "fov" in decl.camera:
        camera["fisheye_fov"] = float(decl.camera["fov"])
    values = {
        **_render_block(decl.render),
        **_ground(decl.render),
        **camera,
        **_sun(decl),
        **_environment(decl.environment),
    }
    if decl.environment and not has_background:
        values["backdrop_sky"] = True
    return replace(settings, **values)


def declared_camera(decl: SceneDeclarations | None, fallback: Camera) -> Camera | None:
    """The camera block as a Camera, or None when the script has none."""
    if decl is None or not decl.camera:
        return None
    block = decl.camera
    eye = _vec(block.get("position")) or fallback.eye
    target = _vec(block.get("target")) or fallback.target
    focus = block.get("focus")
    return Camera(
        eye, target, _vec(block.get("up")) or (0.0, 1.0, 0.0), float(block.get("fov", fallback.fov_y_deg)),
        float(block.get("aperture", 0.0)), float(focus) if isinstance(focus, float) else None,
    )  # fmt: skip
