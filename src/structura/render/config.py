"""The per-render 'cfg' buffer (layout: render/kernels/layout.py) and the camera it encodes."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ..core.color import srgb_to_linear
from ..core.scene.camera import Camera, framed
from ..core.scene.declarations import SceneDeclarations
from ..core.scene.settings import SceneSettings
from .declarations import declared_camera
from .environment import settings_environment
from .filters import filter_table
from .kernels import layout as lay
from .legacy import default_light, legacy_lens
from .lens_config import put_lens
from .lights import light_count
from .settings import RenderSettings

CAUSTIC_FLOOR = 0.3  # GGX alpha after a rough bounce when caustics are filtered
NO_LIMIT = 1e9  # a per-lobe bounce limit that never applies


@dataclass(frozen=True)
class Frame:
    """What the cfg buffer is computed from."""

    camera: Camera
    settings: RenderSettings
    scene: SceneSettings
    radius: float
    world_per_view: float  # legacy view units → world (1/scale), for the default light
    declarations: SceneDeclarations | None = None
    bottom: float = 0.0  # the structure's lowest y (fog base default)


def scene_frame(
    scene: SceneSettings,
    settings: RenderSettings,
    lo: np.ndarray,
    hi: np.ndarray,
    declarations: SceneDeclarations | None = None,
) -> Frame:
    """Decides the view of a render.

    A v2 'camera' block wins over the legacy view; ``settings.frame`` (or a script without a view) frames the
    structure instead.

    Args:
        scene: The script's scene settings (its legacy view).
        settings: The render settings.
        lo: The structure's bounding-box minimum.
        hi: The structure's bounding-box maximum.
        declarations: The script's v2 declarations, if any.

    Returns:
        The frame: camera, settings, scale of the view and the structure's extent.
    """
    camera = scene.view.camera()
    radius = float(np.linalg.norm(np.asarray(hi) - np.asarray(lo))) / 2 or 1.0
    declared = declared_camera(declarations, camera)
    if declared is not None and not settings.frame:  # a v2 'camera' block overrides the legacy view
        return Frame(declared, settings, scene, radius, declared.focus / 20.0, declarations, float(lo[1]))
    world_per_view = 1.0 / scene.view.scale
    camera = with_legacy_dof(camera, settings, scene)
    if settings.frame or not scene.has_view:
        camera = framed(camera, lo, hi, settings.aspect)
        world_per_view = camera.focus / 20.0  # |translation z| of the default legacy view
    return Frame(camera, settings, scene, radius, world_per_view, declarations, float(lo[1]))


def with_legacy_dof(camera: Camera, settings: RenderSettings, scene: SceneSettings) -> Camera:
    """Applies 'set raytracer::dof [centre, falloff]' to a camera as a thin lens.

    Args:
        camera: The camera; one that has depth of field already keeps it.
        settings: The render settings (their ``legacy_dof``).
        scene: The script's scene settings (the legacy view the values are relative to).

    Returns:
        The camera, with the legacy aperture and focus when the script sets them.
    """
    if settings.legacy_dof is None or camera.lens.depth_of_field:
        return camera
    aperture, focus = legacy_lens(scene.view, settings.legacy_dof)
    return camera.with_lens(aperture_radius=aperture, fstop=None).focused_at(focus)


def _put(cfg: np.ndarray, at: int, values: object) -> None:
    v = np.asarray(values, np.float32).ravel()
    cfg[at : at + v.size] = v


def _fog(cfg: np.ndarray, frame: Frame) -> None:
    st = frame.settings
    if st.fog_density > 0:
        cfg[lay.FOG_DENSITY], cfg[lay.FOG_FALLOFF] = st.fog_density, st.fog_falloff
        cfg[lay.FOG_BASE] = frame.bottom if st.fog_base is None else st.fog_base
        _put(cfg, lay.FOG_COLOR, srgb_to_linear(np.asarray(st.fog_color, np.float32)))


def _limit(value: int) -> float:
    return float(value) if value >= 0 else NO_LIMIT


def _sampling(cfg: np.ndarray, st: RenderSettings) -> None:
    cfg[lay.SEQUENCE] = 1.0 if st.sequence == "halton" else 0.0
    cfg[lay.DIFFUSE_BOUNCES] = _limit(st.diffuse_bounces)
    cfg[lay.GLOSSY_BOUNCES] = _limit(st.glossy_bounces)
    cfg[lay.TRANSMISSION_BOUNCES] = _limit(st.transmission_bounces)
    cfg[lay.AO_DIRECT] = 1.0 if st.ao_direct else 0.0


def config(frame: Frame) -> np.ndarray:
    """Returns the render configuration buffer (float32[CFG_SIZE], layout: kernels/layout.py) of a frame.

    Args:
        frame: The camera, settings and scene of the render.
    """
    cam, st = frame.camera, frame.settings
    cfg = np.zeros(lay.CFG_SIZE, np.float32)
    forward, right, up = cam.basis
    for at, v in ((lay.EYE, cam.eye), (lay.FORWARD, forward), (lay.RIGHT, right), (lay.UP, up)):
        _put(cfg, at, v)
    cfg[lay.TAN_HALF], cfg[lay.ASPECT] = math.tan(math.radians(cam.fov_y_deg) / 2), st.aspect
    put_lens(cfg, cam)
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
    cfg[lay.CAUSTIC_ALPHA] = CAUSTIC_FLOOR if st.caustics in ("filtered", "photons") else 0.0
    cfg[lay.BACKDROP_SKY] = 1.0 if st.backdrop_sky else 0.0
    cfg[lay.N_LIGHTS] = light_count(frame.declarations)
    table = None
    if st.filter != "box":
        table, radius = filter_table(st.filter)
        cfg[lay.FILTER_ON], cfg[lay.FILTER_RADIUS] = 1.0, radius
    _fog(cfg, frame)
    _sampling(cfg, st)
    env = settings_environment(st)
    if env is not None:
        cfg[lay.ENV_ON], cfg[lay.ENV_W], cfg[lay.ENV_H] = 1.0, env.width, env.height
        cfg[lay.ENV_ROT], cfg[lay.ENV_SCALE] = math.radians(st.env_rotation_deg), st.env_intensity
    return cfg if table is None else np.concatenate([cfg, table]).astype(np.float32)
