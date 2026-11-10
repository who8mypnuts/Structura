"""Lens options of `structura render` (PLAN Q5): the script's camera, changed from the command line.

--lens "85mm f/1.8"   --focal-length 35   --fov 40   --fstop 2.8   --focus 12 | auto | hyperfocal
--projection fisheye  --sensor aps-c      --shift 0 0.1   --tilt 10 0   --scene-scale 100   --blades 6
"""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from ...core.project.model import camera_from_dict
from ...core.scene.camera import Camera
from ...core.scene.lens import PROJECTIONS, SENSORS, fov_for, parse_lens, sensor_of
from ...render.metadata import read_metadata


def _focus(text: str) -> str | float:
    return text if text in ("auto", "hyperfocal") else float(text)


def add_lens_arguments(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("camera and lens (change the script's camera)")
    g.add_argument("--camera-from", type=Path, metavar="IMAGE", help="the camera of a PNG or EXR Structura rendered")
    g.add_argument("--lens", help='a lens like "85mm f/1.8", "24mm" or "f/2", or a preset name (50mm, 135mm …)')
    g.add_argument("--focal-length", type=float, metavar="MM", help="focal length in millimetres")
    g.add_argument("--fov", type=float, metavar="DEG", help="vertical field of view in degrees")
    g.add_argument("--fstop", type=float, help="aperture as an f-number: depth of field (e.g. 2.8)")
    g.add_argument("--focus", type=_focus, metavar="DIST", help="focus distance, or auto (the target) or hyperfocal")
    g.add_argument("--projection", choices=PROJECTIONS)
    g.add_argument("--sensor", help=f"sensor: {', '.join(SENSORS)} or WxH in mm")
    g.add_argument("--shift", type=float, nargs=2, metavar=("X", "Y"), help="lens shift in frame heights")
    g.add_argument("--tilt", type=float, nargs=2, metavar=("X", "Y"), help="focus-plane tilt in degrees")
    g.add_argument("--scene-scale", type=float, metavar="UNITS", help="world units per metre (for the f-stop)")
    g.add_argument("--blades", type=int, help="aperture blades (3 or more: polygonal bokeh)")


def _lens_changes(args: argparse.Namespace) -> dict[str, object]:
    changes: dict[str, object] = {}
    for arg, field in (("projection", "projection"), ("blades", "blades"), ("scene_scale", "units_per_metre")):
        if getattr(args, arg, None) is not None:
            changes[field] = getattr(args, arg)
    for arg in ("shift", "tilt"):
        if getattr(args, arg, None) is not None:
            changes[arg] = tuple(getattr(args, arg))
    if getattr(args, "sensor", None) is not None:
        sensor = sensor_of(args.sensor)
        if sensor is None:
            raise ValueError(f"--sensor: '{args.sensor}' is not a sensor name or WxH in mm")
        changes["sensor_mm"] = sensor
    return changes


def _camera_from(path: Path) -> Camera:
    try:
        data = json.loads(read_metadata(path).get("camera", "null"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"--camera-from: cannot read {path}: {exc}") from exc
    camera = camera_from_dict(data)
    if camera is None:
        raise ValueError(f"--camera-from: {path.name} carries no Structura camera")
    return camera


def apply_lens_arguments(camera: Camera, args: argparse.Namespace) -> Camera:
    """``camera`` (or the one --camera-from names) with the lens options of the command line (ValueError for a bad
    --lens, --sensor or --camera-from)."""
    if getattr(args, "camera_from", None) is not None:
        camera = _camera_from(args.camera_from)
    camera = camera.with_lens(**_lens_changes(args))
    focal, fstop = parse_lens(args.lens) if getattr(args, "lens", None) else (None, None)
    focal = getattr(args, "focal_length", None) or focal
    if getattr(args, "fov", None) is not None:
        camera = replace(camera, fov_y_deg=args.fov)
    if focal is not None:
        camera = replace(camera, fov_y_deg=fov_for(focal, camera.lens.sensor_mm[1]))
    fstop = getattr(args, "fstop", None) or fstop
    if fstop is not None:
        camera = camera.with_lens(fstop=fstop)
    focus = getattr(args, "focus", None)
    if focus == "hyperfocal":
        camera = camera.with_lens(focus_mode="hyperfocal")
    elif focus is not None:
        camera = camera.focused_at(None if focus == "auto" else float(focus))
    return camera
