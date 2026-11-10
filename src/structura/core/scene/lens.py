"""The camera's lens (PLAN Q5; docs/10 §5): projection, depth of field, bokeh, lens shift and tilt.

One model for the whole program — the viewport, the precision engine, scripts, projects, reports. Simple
settings stay simple: a focal length in millimetres sets the field of view through the sensor size, an f-stop
sets the depth of field through the focal length and the scene's scale, and focus follows the target unless
it is set. Everything photographic converts exactly:

    fov   = 2 · atan(sensor height / (2 · focal length))
    radius = focal length / (2 · f-stop)            (the entrance pupil, in world units)
    CoC   = sensor diagonal / 1500                   (the circle of confusion used for the sharp range)

World units become metres through ``units_per_metre`` (1 by default, Blender's convention); a 20-unit
structure shot at f/2.8 with a 50 mm lens is then a 20 m structure — set the scene scale to make it a
model on a table.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

Pair = tuple[float, float]
PROJECTIONS = ("perspective", "orthographic", "spherical", "fisheye")
FISHEYE_MAPPINGS = ("equidistant", "equisolid", "stereographic")
FOCUS_MODES = ("target", "manual", "hyperfocal")
SENSORS: dict[str, Pair] = {  # width × height, mm
    "full-frame": (36.0, 24.0),
    "aps-c": (23.6, 15.6),
    "mft": (17.3, 13.0),
    "1inch": (13.2, 8.8),
    "phone": (6.4, 4.8),
    "medium-format": (43.8, 32.9),
    "super35": (24.89, 18.66),
}
FULL_FRAME = SENSORS["full-frame"]
COC_DIVISOR = 1500.0
LENS_PRESETS: dict[str, float] = {  # name → focal length (mm, full frame)
    "14mm ultra-wide": 14.0,
    "24mm wide": 24.0,
    "35mm street": 35.0,
    "50mm normal": 50.0,
    "85mm portrait": 85.0,
    "135mm tele": 135.0,
    "200mm long tele": 200.0,
    "100mm macro": 100.0,
}
SIMPLE_FSTOPS = (22.0, 1.2)  # the Depth of field slider runs from the first (deep) to the second (shallow)
LENS_SPEC = re.compile(r"^\s*(?:(\d+(?:\.\d+)?)\s*mm)?\s*(?:f/?(\d+(?:\.\d+)?))?\s*$", re.I)


@dataclass(frozen=True)
class Lens:
    projection: str = "perspective"  # PROJECTIONS
    sensor_mm: Pair = FULL_FRAME  # width, height: relates focal length to the field of view
    fstop: float | None = None  # None: the aperture radius below is used as given
    aperture_radius: float = 0.0  # world units; 0 = pinhole (no depth of field)
    focus_mode: str = "target"  # FOCUS_MODES: the target's distance, focus_distance, or the hyperfocal distance
    focus_distance: float | None = None  # world units (focus_mode 'manual')
    blades: int = 0  # aperture blades: 3 or more give polygonal bokeh
    blade_rotation_deg: float = 0.0
    bokeh_bias: float = 0.0  # −1 centre-weighted (soft) … 0 even … 1 bright rims (catadioptric / old glass)
    anamorphic: float = 1.0  # width / height of the aperture: > 1 gives oval, horizontally stretched bokeh
    shift: Pair = (0.0, 0.0)  # lens shift (x, y) in frame heights: keeps verticals straight in architecture
    tilt: Pair = (0.0, 0.0)  # degrees the focus plane turns about the camera's x and y axes (Scheimpflug)
    ortho_height: float = 10.0  # orthographic: the visible height in world units
    fisheye_fov_deg: float = 180.0  # fisheye: the field across the image height
    fisheye_mapping: str = "equidistant"  # FISHEYE_MAPPINGS
    units_per_metre: float = 1.0  # world units per metre (the f-stop's physical scale)

    @property
    def sensor_diagonal_mm(self) -> float:
        return math.hypot(*self.sensor_mm)

    @property
    def coc_mm(self) -> float:
        return self.sensor_diagonal_mm / COC_DIVISOR

    @property
    def depth_of_field(self) -> bool:
        return self.projection == "perspective" and (self.fstop is not None or self.aperture_radius > 0.0)


def focal_length_mm(fov_y_deg: float, sensor_height_mm: float = FULL_FRAME[1]) -> float:
    """The focal length that gives a vertical field of view ``fov_y_deg`` on a sensor of that height."""
    return sensor_height_mm / (2.0 * math.tan(math.radians(fov_y_deg) / 2.0))


def fov_for(focal_mm: float, sensor_height_mm: float = FULL_FRAME[1]) -> float:
    """The vertical field of view (degrees) of a focal length."""
    return math.degrees(2.0 * math.atan(sensor_height_mm / (2.0 * max(focal_mm, 1e-6))))


def pupil_radius(lens: Lens, focal_mm: float) -> float:
    """The aperture radius in world units: from the f-stop when one is set, else as given."""
    if lens.fstop is None or lens.fstop <= 0.0:
        return lens.aperture_radius
    return focal_mm / 1000.0 * lens.units_per_metre / (2.0 * lens.fstop)


def hyperfocal(lens: Lens, focal_mm: float) -> float:
    """The hyperfocal distance (world units): focused there, everything from half of it to infinity is sharp."""
    radius = pupil_radius(lens, focal_mm)
    if radius <= 0.0:
        return math.inf
    f = focal_mm / 1000.0 * lens.units_per_metre
    coc = lens.coc_mm / 1000.0 * lens.units_per_metre
    return f * (2.0 * radius) / coc + f


def sharp_range(lens: Lens, focal_mm: float, focus: float) -> tuple[float, float]:
    """(near, far) limits of acceptable sharpness around ``focus`` (far is inf beyond the hyperfocal distance)."""
    h = hyperfocal(lens, focal_mm)
    if math.isinf(h):
        return 0.0, math.inf
    f = focal_mm / 1000.0 * lens.units_per_metre
    near = focus * (h - f) / (h + focus - 2.0 * f)
    far = math.inf if focus >= h else focus * (h - f) / (h - focus)
    return near, far


def fstop_for_amount(amount: float) -> float:
    """The Camera panel's 'Depth of field' slider (0 = deep, 1 = shallow) as an f-stop (logarithmic)."""
    deep, shallow = SIMPLE_FSTOPS
    t = min(max(amount, 0.0), 1.0)
    return float(deep * (shallow / deep) ** t)


def amount_for_fstop(fstop: float) -> float:
    deep, shallow = SIMPLE_FSTOPS
    return min(max(math.log(fstop / deep) / math.log(shallow / deep), 0.0), 1.0)


def parse_lens(text: str) -> tuple[float | None, float | None]:
    """'50mm f/2.8', '85mm', 'f2' or a LENS_PRESETS name → (focal length mm, f-stop); ValueError otherwise."""
    key = text.strip().lower()
    preset = next((mm for name, mm in LENS_PRESETS.items() if name.lower() == key or name.split()[0] == key), None)
    if preset is not None:
        return preset, None
    match = LENS_SPEC.match(text)
    if match is None or not (match.group(1) or match.group(2)):
        raise ValueError(f"'{text}' is not a lens: try '50mm', 'f/2.8', '85mm f/1.8' or a preset name")
    return (float(match.group(1)) if match.group(1) else None), (float(match.group(2)) if match.group(2) else None)


def sensor_of(value: object) -> Pair | None:
    """A sensor name ('aps-c'), 'WxH' in mm ('36x24') or a pair of numbers; None when it is not one."""
    if isinstance(value, tuple | list) and len(value) == 2:
        return (float(value[0]), float(value[1]))
    text = str(value).strip().lower()
    if text in SENSORS:
        return SENSORS[text]
    width, _, height = text.partition("x")
    try:
        return (float(width), float(height)) if height else None
    except ValueError:
        return None
