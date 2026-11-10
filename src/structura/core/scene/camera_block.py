"""The v2 'camera { }' block as a Camera with its Lens (docs/05 §9.5; PLAN Q5). camera_script writes the same
keys back. Values were checked against the catalogue already (core/lang/v2/block_check.py)."""

from __future__ import annotations

from typing import Any

from .camera import Camera
from .lens import FISHEYE_MAPPINGS, PROJECTIONS, Lens, fov_for, parse_lens, sensor_of
from .vectors import vec3_of

FLOATS = {"height": "ortho_height", "blade_rotation": "blade_rotation_deg", "bokeh_bias": "bokeh_bias",
          "anamorphic": "anamorphic", "aperture": "aperture_radius", "fstop": "fstop",
          "scale": "units_per_metre"}  # block key → Lens field  # fmt: skip
PAIRS = ("shift", "tilt")


def _pair(value: Any) -> tuple[float, float] | None:
    return (float(value[0]), float(value[1])) if isinstance(value, tuple) and len(value) == 2 else None


def _focus(value: Any) -> dict[str, Any]:
    if isinstance(value, float):
        return {"focus_mode": "manual", "focus_distance": value}
    return {"focus_mode": "hyperfocal"} if str(value).lower() == "hyperfocal" else {}


def lens_from_block(block: dict[str, Any]) -> tuple[Lens, float | None]:
    """(the lens, its focal length in mm when the block gives one)."""
    changes: dict[str, Any] = {field: float(block[key]) for key, field in FLOATS.items() if key in block}
    changes |= {key: pair for key in PAIRS if (pair := _pair(block.get(key))) is not None}
    if str(block.get("type", "")) in PROJECTIONS:
        changes["projection"] = str(block["type"])
    if str(block.get("mapping", "")) in FISHEYE_MAPPINGS:
        changes["fisheye_mapping"] = str(block["mapping"])
    if "blades" in block:
        changes["blades"] = max(0, int(block["blades"]))
    if changes.get("projection") == "fisheye" and "fov" in block:
        changes["fisheye_fov_deg"] = float(block["fov"])
    if (sensor := sensor_of(block["sensor"]) if "sensor" in block else None) is not None:
        changes["sensor_mm"] = sensor
    changes |= _focus(block.get("focus", "auto"))
    focal = float(block["focal_length"]) if "focal_length" in block else None
    if "lens" in block:
        try:
            lens_mm, fstop = parse_lens(str(block["lens"]))
        except ValueError:
            lens_mm, fstop = None, None
        focal = focal or lens_mm
        if fstop is not None and "fstop" not in changes:
            changes["fstop"] = fstop
    return Lens(**changes), focal


def camera_from_block(block: dict[str, Any], fallback: Camera) -> Camera:
    """The camera a block describes; what it leaves out comes from ``fallback`` (the legacy view)."""
    lens, focal = lens_from_block(block)
    fov = fallback.fov_y_deg
    if "fov" in block and lens.projection != "fisheye":
        fov = float(block["fov"])
    if focal is not None:
        fov = fov_for(focal, lens.sensor_mm[1])
    eye, target = vec3_of(block.get("position"), fallback.eye), vec3_of(block.get("target"), fallback.target)
    return Camera(eye, target, vec3_of(block.get("up"), (0.0, 1.0, 0.0)), fov, lens)
