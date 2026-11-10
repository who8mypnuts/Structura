"""Camera → script text (docs/08 §7 "Copy camera to script", docs/07 §5).

v1 scripts get Structure Synth's ``set translation / rotation / pivot / scale`` lines, the exact inverse of
``LegacyView.camera``: the pivot is the target, the rotation's rows are (right, up, −forward), and the
translation puts the eye at the target distance (scale stays at the 1.5 default). v2 scripts get a
``camera { }`` block. ``with_camera`` replaces the script's existing camera lines or block.
"""

from __future__ import annotations

import re

import numpy as np

from .camera import LEGACY_FOV, LEGACY_SCALE, Camera, LegacyView
from .lens import SENSORS, Lens
from .vectors import number as _n
from .vectors import script_vec as _list

V1_KEYS = ("translation", "rotation", "pivot", "scale", "perspective-angle")
V1_LINE = re.compile(r"^[ \t]*set[ \t]+(" + "|".join(map(re.escape, V1_KEYS)) + r")\b[^\n]*\n?", re.MULTILINE | re.I)
V2_BLOCK = re.compile(r"^[ \t]*camera[ \t]*\{[^}]*\}[ \t]*\n?", re.MULTILINE)
MARKER = "// camera (Structura: Copy Camera to Script)"
VERSION_LINE = re.compile(r"^[ \t]*#version[^\n]*\n?", re.MULTILINE)


def legacy_view(camera: Camera) -> LegacyView:
    forward, right, up = camera.basis
    distance = float(np.linalg.norm(np.subtract(camera.target, camera.eye))) or 1.0
    rotation = np.stack([right, up, -forward])
    return LegacyView(
        translation=(0.0, 0.0, -distance * LEGACY_SCALE),
        rotation=tuple(float(v) for v in rotation.ravel()),
        pivot=tuple(float(v) for v in camera.target),  # type: ignore[arg-type]
        scale=LEGACY_SCALE,
        fov_y_deg=camera.fov_y_deg,
    )


def _projection_lines(lens: Lens) -> list[str]:
    if lens.projection == "orthographic":
        return [f"  type orthographic  height {_n(lens.ortho_height)}"]
    if lens.projection == "fisheye":
        mapping = f"  mapping {lens.fisheye_mapping}" if lens.fisheye_mapping != "equidistant" else ""
        return [f"  type fisheye  fov {_n(lens.fisheye_fov_deg)}{mapping}"]
    return [f"  type {lens.projection}"] if lens.projection != "perspective" else []


def _sensor(lens: Lens) -> str:
    name = next((n for n, size in SENSORS.items() if size == lens.sensor_mm), None)
    return name or f"{_n(lens.sensor_mm[0])}x{_n(lens.sensor_mm[1])}"


def _lens_lines(camera: Camera) -> list[str]:
    """The lens keys that differ from a plain pinhole, photographic where the lens is (an f-stop is set)."""
    lens, default = camera.lens, Lens()
    lines = _projection_lines(lens)
    optics = (
        []
        if lens.projection == "fisheye"
        else [  # fisheye: its 'fov' is the lens's field, written above
            f"focal_length {_n(camera.focal_length_mm)}" if lens.fstop else f"fov {_n(camera.fov_y_deg)}"
        ]
    )
    if lens.sensor_mm != default.sensor_mm:
        optics.append(f"sensor {_sensor(lens)}")
    if lens.fstop:
        optics.append(f"fstop {_n(lens.fstop)}")
    elif lens.aperture_radius > 0:
        optics.append(f"aperture {_n(lens.aperture_radius)}")
    if camera.lens.depth_of_field:
        optics.append("focus " + {"manual": _n(camera.focus), "hyperfocal": "hyperfocal"}.get(lens.focus_mode, "auto"))
    lines += ["  " + "  ".join(optics)] if optics else []
    extra = [f"{key} {value}" for key, value, changed in (
        ("scale", _n(lens.units_per_metre), lens.units_per_metre != default.units_per_metre),
        ("blades", str(lens.blades), lens.blades != default.blades),
        ("blade_rotation", _n(lens.blade_rotation_deg), lens.blade_rotation_deg != default.blade_rotation_deg),
        ("bokeh_bias", _n(lens.bokeh_bias), lens.bokeh_bias != default.bokeh_bias),
        ("anamorphic", _n(lens.anamorphic), lens.anamorphic != default.anamorphic),
        ("shift", _list(lens.shift), lens.shift != default.shift),
        ("tilt", _list(lens.tilt), lens.tilt != default.tilt),
    ) if changed]  # fmt: skip
    return [*lines, *(["  " + "  ".join(extra)] if extra else [])]


def camera_text(camera: Camera, v2: bool) -> str:
    """Writes a camera as script lines.

    Args:
        camera: The camera to write (its lens too, in v2).
        v2: True for a v2 'camera { }' block with its lens, False for Structure Synth's 'set' lines.

    Returns:
        The lines, without a trailing newline.
    """
    if v2:
        place = f"  position {_list(camera.eye)}  target {_list(camera.target)}  up {_list(camera.up)}"
        return "\n".join(["camera {", place, *_lens_lines(camera), "}"])
    view = legacy_view(camera)
    lines = [MARKER, f"set translation {_list(view.translation)}", f"set rotation {_list(view.rotation)}",
             f"set pivot {_list(view.pivot)}", f"set scale {_n(view.scale)}"]  # fmt: skip
    if abs(camera.fov_y_deg - LEGACY_FOV) > 1e-9:
        lines.append(f"set perspective-angle {_n(camera.fov_y_deg)}")
    return "\n".join(lines)


def with_camera(text: str, camera: Camera, v2: bool) -> str:
    """``text`` with its camera lines (v1) or camera block (v2) replaced by ``camera``, at the top (after a
    '#version' line)."""
    body = V2_BLOCK.sub("", text) if v2 else V1_LINE.sub("", text)
    body = body.replace(MARKER + "\n", "")
    version = VERSION_LINE.match(body)
    head, rest = (body[: version.end()], body[version.end() :]) if version else ("", body)
    return f"{head}{camera_text(camera, v2)}\n\n{rest.lstrip(chr(10))}"
