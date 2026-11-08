"""Render settings (docs/09). Field names follow docs/05 §9.5 ('render {}' block)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..core.params import ParamSpec, ParamType
from .ground import MODES as GROUND_MODES
from .ground import Ground
from .kernels import layout as lay
from .kernels.layout import CAMERA_TYPES

INTEGRATORS = {
    "preview": lay.INTEGRATOR_PREVIEW,
    "ao": lay.INTEGRATOR_AO,
    "path": lay.INTEGRATOR_PATH,
    "classic": lay.INTEGRATOR_CLASSIC,
}
VIEWS = ("auto", "agx", "standard", "soft", "aces", "filmic")  # render/views.py; auto: agx, classic → standard
ENV_TYPES = ("gradient", "hdri", "sunsky")
AUTO_PASSES = 0  # samples_per_pass: size passes by device time (render/pacing.py)
FILTER_NAMES = ("box", "triangle", "gaussian", "blackman-harris", "mitchell", "catmull-rom", "bspline", "lanczos",
                "sinc")  # fmt: skip
SAMPLERS = ("progressive", "tiled")  # docs/09 §5: whole-image passes, or buckets refined one at a time
BUCKET_ORDERS = ("hilbert", "spiral", "rows", "columns", "diagonal", "random")
SEQUENCES = ("random", "halton")  # hashed per-pixel random numbers, or Halton (Sunflow's QMC, for comparison)


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
    caustics: str = "filtered"  # filtered: glossy lobes blurred after a rough bounce; on: unbiased; photons
    photon_count: int = 300_000  # caustics "photons": sun photons traced per render
    photon_radius: float = 0.0  # gather radius in world units (0: 0.6 % of the scene's bounding radius)
    view: str = "auto"
    camera_type: str = "perspective"  # perspective | orthographic | spherical | fisheye
    ortho_height: float = 10.0  # orthographic: visible height in world units
    fisheye_fov: float = 180.0  # fisheye: field of view across the image height, degrees
    frame: bool = False  # ignore the script camera and fit the structure
    seed: int = 0
    env_type: str = "gradient"  # gradient (sky_top/bottom) | hdri (env_file) | sunsky (Preetham, lit by the sun)
    env_file: str = ""  # .exr / .hdr; relative paths are resolved against asset_dir
    env_rotation_deg: float = 0.0
    env_intensity: float = 1.0
    turbidity: float = 3.0
    ground: tuple[float, float, float] = (0.06, 0.055, 0.05)  # sunsky: the ground below the horizon (linear)
    asset_dir: str = ""  # the script's folder (for relative file names)
    filter: str = "box"  # pixel reconstruction filter (render/filters.py); box = uniform jitter in the pixel
    blades: int = 0  # aperture blades for polygonal bokeh (< 3: a round aperture)
    blade_rotation_deg: float = 0.0
    region: tuple[int, int, int, int] | None = None  # x0, y0, x1, y1 (pixels): render only this rectangle
    aovs: bool = False  # also compute first-hit albedo / normal / depth / ids (EXR layers, denoising)
    noise_threshold: float = 0.0  # adaptive sampling: pixels stop once their relative error is below (0 = off)
    adaptive_min_samples: int = 16  # samples every pixel gets before the noise test starts
    time_limit: float = 0.0  # seconds; stop after the pass that crosses it (0 = no limit)
    ground_plane: str = "off"  # off | plane | catcher (render/ground.py)
    ground_color: tuple[float, float, float] = (0.8, 0.8, 0.8)  # sRGB
    ground_offset: float = 0.0  # below the scene's lowest point, world units
    fog_density: float = 0.0  # per world unit at the fog base (0 = no fog; kernels/fog.py)
    fog_falloff: float = 0.0  # height over which the density falls by e (0 = homogeneous)
    fog_base: float | None = None  # height of full density (None: the structure's lowest point)
    fog_color: tuple[float, float, float] = (0.8, 0.85, 0.9)  # sRGB
    sampler: str = "progressive"  # SAMPLERS
    bucket_size: int = 64  # tiled: bucket edge in pixels
    bucket_order: str = "hilbert"  # tiled: BUCKET_ORDERS
    sequence: str = "random"  # SEQUENCES
    diffuse_bounces: int = -1  # path: per-lobe limits within max_bounces (-1 = no separate limit)
    glossy_bounces: int = -1
    transmission_bounces: int = -1
    ao_direct: bool = False  # ao: add direct light from the sun and the declared lights
    mosaic: bool = False  # progressive: a quarter-resolution first image before the first full pass (the GUI)

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
        return "standard" if self.integrator == "classic" else "agx"

    @property
    def ground_spec(self) -> Ground | None:
        if self.ground_plane not in ("plane", "catcher"):
            return None
        return Ground(self.ground_plane == "catcher", self.ground_color, self.ground_offset)

    @property
    def aspect(self) -> float:
        return self.width / self.height


def render_param_specs() -> tuple[ParamSpec, ...]:
    """The user-adjustable render settings (the Render Settings panel; docs/14 §3)."""
    return (
        ParamSpec("sampler", ParamType.ENUM, "progressive", "Image sampler", choices=SAMPLERS),
        ParamSpec("bucket_size", ParamType.INT, 64, "Bucket size (tiled)", range=(8, 512)),
        ParamSpec("bucket_order", ParamType.ENUM, "hilbert", "Bucket order (tiled)", choices=BUCKET_ORDERS),
        ParamSpec("sequence", ParamType.ENUM, "random", "Sample sequence", choices=SEQUENCES),
        ParamSpec("max_bounces", ParamType.INT, 4, "Max bounces", range=(0, 64)),
        ParamSpec("diffuse_bounces", ParamType.INT, -1, "Diffuse bounces (-1 = max)", range=(-1, 64)),
        ParamSpec("glossy_bounces", ParamType.INT, -1, "Glossy bounces (-1 = max)", range=(-1, 64)),
        ParamSpec("transmission_bounces", ParamType.INT, -1, "Transmission bounces (-1 = max)", range=(-1, 64)),
        ParamSpec("ao_samples", ParamType.INT, 8, "AO samples", range=(0, 256)),
        ParamSpec("ao_direct", ParamType.BOOL, False, "AO: add direct light"),
        ParamSpec("sun_elevation_deg", ParamType.FLOAT, 50.0, "Sun elevation °", range=(-90.0, 90.0)),
        ParamSpec("sun_azimuth_deg", ParamType.FLOAT, 35.0, "Sun azimuth °", range=(-360.0, 360.0)),
        ParamSpec("sun_angle_deg", ParamType.FLOAT, 2.0, "Sun size °", range=(0.01, 45.0)),
        ParamSpec("clamp", ParamType.FLOAT, 20.0, "Sample clamp", range=(0.1, 1e6)),
        ParamSpec("noise_threshold", ParamType.FLOAT, 0.0, "Noise threshold (0 = off)", range=(0.0, 1.0)),
        ParamSpec("time_limit", ParamType.FLOAT, 0.0, "Time limit, s (0 = none)", range=(0.0, 1e6)),
        ParamSpec("aperture", ParamType.FLOAT, 0.0, "Aperture radius", range=(0.0, 100.0)),
        ParamSpec("camera_type", ParamType.ENUM, "perspective", "Camera", choices=tuple(CAMERA_TYPES)),
        ParamSpec("caustics", ParamType.ENUM, "filtered", "Caustics", choices=("filtered", "on", "photons")),
        ParamSpec("photon_count", ParamType.INT, 300_000, "Caustic photons", range=(1000, 100_000_000)),
        ParamSpec("photon_radius", ParamType.FLOAT, 0.0, "Photon radius (0 = auto)", range=(0.0, 1e6)),
        ParamSpec("view", ParamType.ENUM, "auto", "View transform", choices=VIEWS),
        ParamSpec("filter", ParamType.ENUM, "box", "Pixel filter", choices=FILTER_NAMES),
        ParamSpec("blades", ParamType.INT, 0, "Aperture blades (bokeh)", range=(0, 16)),
        ParamSpec("blade_rotation_deg", ParamType.FLOAT, 0.0, "Blade rotation °", range=(-360.0, 360.0)),
        ParamSpec("env_type", ParamType.ENUM, "gradient", "Environment", choices=ENV_TYPES),
        ParamSpec("env_file", ParamType.STRING, "", "HDRI file (.exr / .hdr)"),
        ParamSpec("env_rotation_deg", ParamType.FLOAT, 0.0, "Environment rotation °", range=(-360.0, 360.0)),
        ParamSpec("env_intensity", ParamType.FLOAT, 1.0, "Environment intensity", range=(0.0, 1000.0)),
        ParamSpec("turbidity", ParamType.FLOAT, 3.0, "Sky turbidity", range=(1.7, 10.0)),
        ParamSpec("fog_density", ParamType.FLOAT, 0.0, "Fog density", range=(0.0, 1e3)),
        ParamSpec("fog_falloff", ParamType.FLOAT, 0.0, "Fog falloff height (0 = even)", range=(0.0, 1e6)),
        ParamSpec("ground_plane", ParamType.ENUM, "off", "Ground", choices=GROUND_MODES),
        ParamSpec("ground_offset", ParamType.FLOAT, 0.0, "Ground offset", range=(-1e6, 1e6)),
        ParamSpec("shadows", ParamType.BOOL, True, "Shadows (classic)"),
    )
