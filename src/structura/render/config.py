"""The per-render 'cfg' buffer (layout: render/kernels/layout.py) and the camera it encodes."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np

from ..core.color import srgb_to_linear
from ..core.scene.camera import Camera, framed
from ..core.scene.declarations import SceneDeclarations
from ..core.scene.settings import SceneSettings
from .declarations import declared_camera
from .kernels import layout as lay
from .legacy import default_light, legacy_lens
from .lights import light_count
from .settings import RenderSettings

CAUSTIC_FLOOR = 0.3  # GGX alpha after a rough bounce when caustics are filtered


@dataclass(frozen=True)
class Frame:
    """What the cfg buffer is computed from."""

    camera: Camera
    settings: RenderSettings
    scene: SceneSettings
    radius: float
    world_per_view: float  # legacy view units → world (1/scale), for the default light
    declarations: SceneDeclarations | None = None


def scene_frame(
    scene: SceneSettings,
    settings: RenderSettings,
    lo: np.ndarray,
    hi: np.ndarray,
    declarations: SceneDeclarations | None = None,
) -> Frame:
    camera = scene.view.camera()
    declared = declared_camera(declarations, camera)
    if declared is not None and not settings.frame:  # a v2 'camera' block overrides the legacy view
        radius = float(np.linalg.norm(np.asarray(hi) - np.asarray(lo))) / 2 or 1.0
        return Frame(declared, settings, scene, radius, declared.focus / 20.0, declarations)
    world_per_view = 1.0 / scene.view.scale
    if settings.legacy_dof is not None and settings.aperture == 0.0:
        aperture, focus = legacy_lens(scene.view, settings.legacy_dof)
        camera = replace(camera, aperture_radius=aperture, focus_distance=focus)
    if settings.frame or not scene.has_view:
        camera = framed(camera, lo, hi, settings.aspect)
        world_per_view = camera.focus / 20.0  # |translation z| of the default legacy view
    radius = float(np.linalg.norm(np.asarray(hi) - np.asarray(lo))) / 2 or 1.0
    return Frame(camera, settings, scene, radius, world_per_view, declarations)


def _put(cfg: np.ndarray, at: int, values: object) -> None:
    v = np.asarray(values, np.float32).ravel()
    cfg[at : at + v.size] = v


def config(frame: Frame) -> np.ndarray:
    cam, st = frame.camera, frame.settings
    cfg = np.zeros(lay.CFG_SIZE, np.float32)
    forward, right, up = cam.basis
    for at, v in ((lay.EYE, cam.eye), (lay.FORWARD, forward), (lay.RIGHT, right), (lay.UP, up)):
        _put(cfg, at, v)
    cfg[lay.TAN_HALF], cfg[lay.ASPECT] = math.tan(math.radians(cam.fov_y_deg) / 2), st.aspect
    cfg[lay.APERTURE] = st.aperture or cam.aperture_radius
    cfg[lay.FOCUS] = st.focus_distance or cam.focus
    _put(cfg, lay.BACKGROUND, srgb_to_linear(np.asarray(frame.scene.background, np.float32)))
    cfg[lay.EPS] = 1e-4
    _put(cfg, lay.SUN_DIR, st.sun_direction)
    cfg[lay.SUN_COS] = math.cos(math.radians(st.sun_angle_deg) / 2)
    _put(cfg, lay.SUN_IRRADIANCE, st.sun_irradiance)
    cfg[lay.AO_DIST] = st.ao_distance or frame.radius * 0.3
    _put(cfg, lay.SKY_TOP, st.sky_top)
    _put(cfg, lay.SKY_BOTTOM, st.sky_bottom)
    cfg[lay.CLAMP] = st.clamp
    _put(cfg, lay.LIGHT_POS, st.light_position or default_light(cam, st.aspect, frame.world_per_view))
    cfg[lay.SHADOWS] = 1.0 if st.shadows else 0.0
    cfg[lay.CAUSTIC_ALPHA] = CAUSTIC_FLOOR if st.caustics == "filtered" else 0.0
    cfg[lay.BACKDROP_SKY] = 1.0 if st.backdrop_sky else 0.0
    cfg[lay.N_LIGHTS] = light_count(frame.declarations)
    cfg[lay.CAM_TYPE] = lay.CAMERA_TYPES.get(st.camera_type, 0)
    cfg[lay.ORTHO_HALF], cfg[lay.FISHEYE_FOV] = st.ortho_height / 2, math.radians(st.fisheye_fov)
    return cfg
