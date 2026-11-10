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
    """Lens fields of a 'focus' value: a distance, 'hyperfocal', or nothing for 'auto' (the target)."""
    if isinstance(value, float):
        return {"focus_mode": "manual", "focus_distance": value}
    return {"focus_mode": "hyperfocal"} if str(value).lower() == "hyperfocal" else {}


def _lens_key(block: dict[str, Any]) -> tuple[float | None, float | None]:
    """(focal length, f-stop) of a 'lens' key ('85mm f/1.8', a preset name); (None, None) without one."""
    try:
        return parse_lens(str(block["lens"])) if "lens" in block else (None, None)
    except ValueError:  # (block_check reports it; the camera keeps its other values)
        return None, None


def lens_from_block(block: dict[str, Any]) -> tuple[Lens, float | None]:
    """Reads the lens of a camera block.

    Args:
        block: The block's checked entries (key → value as parse_body read it).

    Returns:
        (the lens, the focal length in mm when the block sets one through 'focal_length' or 'lens').
        'focal_length' wins over 'lens'; an explicit 'fstop' wins over the one in 'lens'.
    """
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
    lens_mm, lens_fstop = _lens_key(block)
    if lens_fstop is not None:
        changes.setdefault("fstop", lens_fstop)
    focal = float(block["focal_length"]) if "focal_length" in block else lens_mm
    return Lens(**changes), focal


def camera_from_block(block: dict[str, Any], fallback: Camera) -> Camera:
    """Reads a camera block.

    Args:
        block: The block's checked entries.
        fallback: The camera that supplies what the block leaves out (the script's legacy view).

    Returns:
        The camera; a focal length overrides 'fov' (fisheye lenses keep 'fov' as their own field).
    """
    lens, focal = lens_from_block(block)
    fov = fallback.fov_y_deg
    if "fov" in block and lens.projection != "fisheye":
        fov = float(block["fov"])
    if focal is not None:
        fov = fov_for(focal, lens.sensor_mm[1])
    eye, target = vec3_of(block.get("position"), fallback.eye), vec3_of(block.get("target"), fallback.target)
    return Camera(eye, target, vec3_of(block.get("up"), (0.0, 1.0, 0.0)), fov, lens)
