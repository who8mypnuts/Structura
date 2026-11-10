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


MIN_FOV_DEG, MAX_FOV_DEG = 1e-3, 179.0  # a perspective field of view is kept inside this open range


@dataclass(frozen=True)
class Lens:
    """A camera lens: projection, sensor, aperture, focus, bokeh, shift and tilt.

    Attributes:
        projection: One of PROJECTIONS.
        sensor_mm: Sensor width and height in millimetres; relates focal length and field of view.
        fstop: The f-number; None uses ``aperture_radius`` as given.
        aperture_radius: Entrance-pupil radius in world units when no f-stop is set (0: a pinhole).
        focus_mode: One of FOCUS_MODES: the target's distance, ``focus_distance`` or the hyperfocal distance.
        focus_distance: The distance in focus in world units ('manual' focus).
        blades: Aperture blades; three or more give polygonal bokeh.
        blade_rotation_deg: Rotation of the blade polygon.
        bokeh_bias: −1 brightens the bokeh's centre, 0 is even, 1 brightens its rim.
        anamorphic: Aperture width / height; above 1 stretches the bokeh horizontally.
        shift: Lens shift (x, y) in frame heights (straight verticals in architecture).
        tilt: Degrees the focus plane turns about the camera's x and y axes (Scheimpflug).
        ortho_height: Visible height in world units (orthographic projection).
        fisheye_fov_deg: Field of view across the image height (fisheye projection).
        fisheye_mapping: One of FISHEYE_MAPPINGS.
        units_per_metre: World units per metre: the physical scale the f-stop works at.
    """

    projection: str = "perspective"
    sensor_mm: Pair = FULL_FRAME
    fstop: float | None = None
    aperture_radius: float = 0.0
    focus_mode: str = "target"
    focus_distance: float | None = None
    blades: int = 0
    blade_rotation_deg: float = 0.0
    bokeh_bias: float = 0.0
    anamorphic: float = 1.0
    shift: Pair = (0.0, 0.0)
    tilt: Pair = (0.0, 0.0)
    ortho_height: float = 10.0
    fisheye_fov_deg: float = 180.0
    fisheye_mapping: str = "equidistant"
    units_per_metre: float = 1.0

    @property
    def sensor_diagonal_mm(self) -> float:
        """The sensor's diagonal in millimetres."""
        return math.hypot(*self.sensor_mm)

    @property
    def coc_mm(self) -> float:
        """The circle of confusion in millimetres (the sensor diagonal / COC_DIVISOR)."""
        return self.sensor_diagonal_mm / COC_DIVISOR

    @property
    def depth_of_field(self) -> bool:
        """Whether the lens blurs anything: a perspective lens with an f-stop or an aperture."""
        return self.projection == "perspective" and (self.fstop is not None or self.aperture_radius > 0.0)

    def world(self, millimetres: float) -> float:
        """Converts a physical length in millimetres to world units at the lens's scale.

        Args:
            millimetres: A length such as a focal length or a circle of confusion.

        Returns:
            The length in world units (``units_per_metre`` world units make a metre).
        """
        return millimetres / 1000.0 * self.units_per_metre


def focal_length_mm(fov_y_deg: float, sensor_height_mm: float = FULL_FRAME[1]) -> float:
    """Returns the focal length that gives a vertical field of view on a sensor.

    Args:
        fov_y_deg: Vertical field of view in degrees (clamped to MIN_FOV_DEG … MAX_FOV_DEG).
        sensor_height_mm: Height of the sensor in millimetres.

    Returns:
        The focal length in millimetres.
    """
    fov = min(max(fov_y_deg, MIN_FOV_DEG), MAX_FOV_DEG)
    return sensor_height_mm / (2.0 * math.tan(math.radians(fov) / 2.0))


def fov_for(focal_mm: float, sensor_height_mm: float = FULL_FRAME[1]) -> float:
    """Returns the vertical field of view, in degrees, of a focal length on a sensor.

    Args:
        focal_mm: Focal length in millimetres (at least 1e-6).
        sensor_height_mm: Height of the sensor in millimetres.

    Returns:
        The vertical field of view in degrees.
    """
    return math.degrees(2.0 * math.atan(sensor_height_mm / (2.0 * max(focal_mm, 1e-6))))


def pupil_radius(lens: Lens, focal_mm: float) -> float:
    """Returns the entrance-pupil radius in world units.

    Args:
        lens: The lens; its f-stop (when set and positive) decides, else its ``aperture_radius``.
        focal_mm: The focal length in millimetres.

    Returns:
        The radius in world units (0 for a pinhole).
    """
    if lens.fstop is None or lens.fstop <= 0.0:
        return lens.aperture_radius
    return lens.world(focal_mm) / (2.0 * lens.fstop)


def hyperfocal(lens: Lens, focal_mm: float) -> float:
    """Returns the hyperfocal distance: focused there, everything from half of it to infinity is sharp.

    Args:
        lens: The lens (aperture, sensor and scale).
        focal_mm: The focal length in millimetres.

    Returns:
        The distance in world units; ``math.inf`` for a pinhole.
    """
    radius = pupil_radius(lens, focal_mm)
    if radius <= 0.0:
        return math.inf
    f = lens.world(focal_mm)
    return f * (2.0 * radius) / lens.world(lens.coc_mm) + f


def sharp_range(lens: Lens, focal_mm: float, focus: float) -> tuple[float, float]:
    """Returns the near and far limits of acceptable sharpness around a focus distance.

    Args:
        lens: The lens (aperture, sensor and scale).
        focal_mm: The focal length in millimetres.
        focus: The distance in focus, in world units.

    Returns:
        (near, far) in world units; far is ``math.inf`` at or beyond the hyperfocal distance, and a pinhole
        gives (0, inf).
    """
    h = hyperfocal(lens, focal_mm)
    if math.isinf(h):
        return 0.0, math.inf
    f = lens.world(focal_mm)
    near = focus * (h - f) / (h + focus - 2.0 * f)
    far = math.inf if focus >= h else focus * (h - f) / (h - focus)
    return near, far


def fstop_for_amount(amount: float) -> float:
    """Maps the Camera panel's 'Depth of field' slider to an f-stop, logarithmically.

    Args:
        amount: 0 (deep: SIMPLE_FSTOPS[0]) … 1 (shallow: SIMPLE_FSTOPS[1]); clamped to that range.

    Returns:
        The f-stop.
    """
    deep, shallow = SIMPLE_FSTOPS
    t = min(max(amount, 0.0), 1.0)
    return float(deep * (shallow / deep) ** t)


def amount_for_fstop(fstop: float) -> float:
    """Maps an f-stop back to the 'Depth of field' slider; the inverse of ``fstop_for_amount``.

    Args:
        fstop: An f-stop; values outside SIMPLE_FSTOPS (or not positive) give the nearest end.

    Returns:
        The slider amount in 0 … 1.
    """
    deep, shallow = SIMPLE_FSTOPS
    if fstop <= 0.0 or not math.isfinite(fstop):
        return 0.0
    return min(max(math.log(fstop / deep) / math.log(shallow / deep), 0.0), 1.0)


def parse_lens(text: str) -> tuple[float | None, float | None]:
    """Reads a lens description.

    Args:
        text: '50mm f/2.8', '85mm', 'f2' or a LENS_PRESETS name (or its first word, '85mm').

    Returns:
        (focal length in mm, f-stop); either is None when the text leaves it out.

    Raises:
        ValueError: The text is not a lens.
    """
    key = text.strip().lower()
    preset = next((mm for name, mm in LENS_PRESETS.items() if name.lower() == key or name.split()[0] == key), None)
    if preset is not None:
        return preset, None
    match = LENS_SPEC.match(text)
    if match is None or not (match.group(1) or match.group(2)):
        raise ValueError(f"'{text}' is not a lens: try '50mm', 'f/2.8', '85mm f/1.8' or a preset name")
    return (float(match.group(1)) if match.group(1) else None), (float(match.group(2)) if match.group(2) else None)


def sensor_of(value: object) -> Pair | None:
    """Reads a sensor size.

    Args:
        value: A SENSORS name ('aps-c'), 'WxH' in millimetres ('36x24') or a pair of numbers.

    Returns:
        (width, height) in millimetres, or None when ``value`` is not a sensor with a positive size.
    """
    size: Pair | None = None
    text = str(value).strip().lower()
    try:
        if isinstance(value, tuple | list) and len(value) == 2:
            size = (float(value[0]), float(value[1]))
        elif text in SENSORS:
            size = SENSORS[text]
        elif "x" in text:
            width, _, height = text.partition("x")
            size = (float(width), float(height))
    except (TypeError, ValueError):
        return None
    return size if size is not None and size[0] > 0.0 and size[1] > 0.0 else None
