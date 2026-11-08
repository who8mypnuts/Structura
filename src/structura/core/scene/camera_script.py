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

V1_KEYS = ("translation", "rotation", "pivot", "scale", "perspective-angle")
V1_LINE = re.compile(r"^[ \t]*set[ \t]+(" + "|".join(map(re.escape, V1_KEYS)) + r")\b[^\n]*\n?", re.MULTILINE | re.I)
V2_BLOCK = re.compile(r"^[ \t]*camera[ \t]*\{[^}]*\}[ \t]*\n?", re.MULTILINE)
MARKER = "// camera (Structura: Copy Camera to Script)"
VERSION_LINE = re.compile(r"^[ \t]*#version[^\n]*\n?", re.MULTILINE)


def _n(x: float) -> str:
    text = f"{float(x):.6g}"
    return "0" if text in ("-0", "0") else text


def _list(values: object) -> str:
    return "[" + " ".join(_n(v) for v in values) + "]"  # type: ignore[attr-defined]


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


def camera_text(camera: Camera, v2: bool) -> str:
    """The camera as script lines (no trailing blank line)."""
    if v2:
        lines = ["camera {", f"  position {_list(camera.eye)}  target {_list(camera.target)}  up {_list(camera.up)}",
                 f"  fov {_n(camera.fov_y_deg)}"]  # fmt: skip
        if camera.aperture_radius > 0:
            focus = _n(camera.focus_distance) if camera.focus_distance else "auto"
            lines.append(f"  aperture {_n(camera.aperture_radius)}  focus {focus}")
        return "\n".join([*lines, "}"])
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
