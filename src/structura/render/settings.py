"""Render settings (docs/09). Field names follow docs/05 §9.5 ('render {}' block)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..core.params import ParamSpec, ParamType
from .kernels import layout as lay
from .kernels.layout import CAMERA_TYPES

INTEGRATORS = {
    "preview": lay.INTEGRATOR_PREVIEW,
    "ao": lay.INTEGRATOR_AO,
    "path": lay.INTEGRATOR_PATH,
    "classic": lay.INTEGRATOR_CLASSIC,
}
VIEWS = ("auto", "standard", "soft")  # standard: plain sRGB clip; soft: highlight roll-off


@dataclass(frozen=True)
class RenderSettings:
    width: int = 640
    height: int = 480
    samples: int = 64
    samples_per_pass: int = 4
    integrator: str = "path"
    max_bounces: int = 4
    ao_samples: int = 8
    ao_distance: float | None = None  # None: 30% of the scene radius
    sun_elevation_deg: float = 50.0
    sun_azimuth_deg: float = 35.0
    sun_angle_deg: float = 2.0  # angular diameter
    sun_vector: tuple[float, float, float] | None = None  # explicit direction towards the sun (v2 'light')
    sun_irradiance: tuple[float, float, float] = (3.2, 3.0, 2.7)
    sky_top: tuple[float, float, float] = (0.55, 0.65, 0.85)
    sky_bottom: tuple[float, float, float] = (0.25, 0.24, 0.22)
    clamp: float = 20.0
    aperture: float = 0.0
    focus_distance: float | None = None
    legacy_dof: tuple[float, float] | None = None  # 'raytracer::dof [center, falloff]', resolved with the view
    light_position: tuple[float, float, float] | None = None  # classic point light; None: the 1.5 default
    shadows: bool = True
    backdrop_sky: bool = False  # camera rays that miss show the environment (v2 'environment' without background)
    caustics: str = "filtered"  # filtered: glossy lobes are blurred after a rough bounce; "on": unbiased
    view: str = "auto"
    camera_type: str = "perspective"  # perspective | orthographic | spherical | fisheye
    ortho_height: float = 10.0  # orthographic: visible height in world units
    fisheye_fov: float = 180.0  # fisheye: field of view across the image height, degrees
    frame: bool = False  # ignore the script camera and fit the structure
    seed: int = 0

    @property
    def sun_direction(self) -> tuple[float, float, float]:
        if self.sun_vector is not None:
            return self.sun_vector
        el, az = math.radians(self.sun_elevation_deg), math.radians(self.sun_azimuth_deg)
        return (math.cos(el) * math.sin(az), math.sin(el), math.cos(el) * math.cos(az))

    @property
    def view_transform(self) -> str:
        if self.view != "auto":
            return self.view
        return "standard" if self.integrator == "classic" else "soft"

    @property
    def aspect(self) -> float:
        return self.width / self.height


def render_param_specs() -> tuple[ParamSpec, ...]:
    """The user-adjustable render settings (the Render Settings panel; docs/14 §3)."""
    return (
        ParamSpec("max_bounces", ParamType.INT, 4, "Max bounces", range=(0, 64)),
        ParamSpec("ao_samples", ParamType.INT, 8, "AO samples", range=(0, 256)),
        ParamSpec("sun_elevation_deg", ParamType.FLOAT, 50.0, "Sun elevation °", range=(-90.0, 90.0)),
        ParamSpec("sun_azimuth_deg", ParamType.FLOAT, 35.0, "Sun azimuth °", range=(-360.0, 360.0)),
        ParamSpec("sun_angle_deg", ParamType.FLOAT, 2.0, "Sun size °", range=(0.01, 45.0)),
        ParamSpec("clamp", ParamType.FLOAT, 20.0, "Sample clamp", range=(0.1, 1e6)),
        ParamSpec("aperture", ParamType.FLOAT, 0.0, "Aperture radius", range=(0.0, 100.0)),
        ParamSpec("camera_type", ParamType.ENUM, "perspective", "Camera", choices=tuple(CAMERA_TYPES)),
        ParamSpec("caustics", ParamType.ENUM, "filtered", "Caustics", choices=("filtered", "on")),
        ParamSpec("view", ParamType.ENUM, "auto", "View transform", choices=VIEWS),
        ParamSpec("shadows", ParamType.BOOL, True, "Shadows (classic)"),
    )
