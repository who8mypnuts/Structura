"""Camera rays: pinhole or thin lens (uniform disc aperture), configured through the cfg buffer."""

from __future__ import annotations

from structura.kernels.skl import PI, Buf, cos, f32, floor, func, normalize, sin, sqrt, struct, u32, vec3

from .layout import (
    APERTURE,
    ASPECT,
    BLADE_ROT,
    BLADES,
    CAM_TYPE,
    EYE,
    FISHEYE_FOV,
    FOCUS,
    FORWARD,
    ORTHO_HALF,
    RIGHT,
    TAN_HALF,
    UP,
)


@struct
class Ray:
    o: vec3
    d: vec3


@func
def cfg3(cfg: Buf[f32], at: u32) -> vec3:
    return vec3(cfg[at], cfg[at + 1], cfg[at + 2])


@func
def panoramic_ray(cfg: Buf[f32], sx: f32, sy: f32) -> Ray:
    """Spherical (equirectangular 360°) or equidistant fisheye directions around the camera basis."""
    f = cfg3(cfg, FORWARD)
    r = cfg3(cfg, RIGHT)
    u = cfg3(cfg, UP)
    if cfg[CAM_TYPE] == 2.0:
        phi = sx * PI
        theta = sy * 0.5 * PI
        ring = f * (cos(theta) * cos(phi)) + r * (cos(theta) * sin(phi))
        return Ray(cfg3(cfg, EYE), normalize(ring + u * sin(theta)))
    px = sx * cfg[ASPECT]
    radius = sqrt(px * px + sy * sy)
    angle = radius * 0.5 * cfg[FISHEYE_FOV]
    s = sin(angle) / max(radius, 1.0e-6)
    return Ray(cfg3(cfg, EYE), normalize(f * cos(angle) + r * (px * s) + u * (sy * s)))


@func
def camera_ray(cfg: Buf[f32], sx: f32, sy: f32, u1: f32, u2: f32) -> Ray:
    """Ray through normalised screen position (sx, sy) ∈ [-1,1]² (y up); u1/u2 sample the lens."""
    if cfg[CAM_TYPE] >= 2.0:
        return panoramic_ray(cfg, sx, sy)
    if cfg[CAM_TYPE] == 1.0:
        offset = cfg3(cfg, RIGHT) * (sx * cfg[ORTHO_HALF] * cfg[ASPECT]) + cfg3(cfg, UP) * (sy * cfg[ORTHO_HALF])
        return Ray(cfg3(cfg, EYE) + offset, cfg3(cfg, FORWARD))
    eye = cfg3(cfg, EYE)
    d = normalize(
        cfg3(cfg, FORWARD)
        + cfg3(cfg, RIGHT) * (sx * cfg[TAN_HALF] * cfg[ASPECT])
        + cfg3(cfg, UP) * (sy * cfg[TAN_HALF])
    )
    if cfg[APERTURE] <= 0.0:
        return Ray(eye, d)
    focus_point = eye + d * (
        cfg[FOCUS] / max(1.0e-6, d.x * cfg[FORWARD] + d.y * cfg[FORWARD + 1] + d.z * cfg[FORWARD + 2])
    )
    lx = lens_x(cfg, u1, u2)
    ly = lens_y(cfg, u1, u2)
    lens = eye + cfg3(cfg, RIGHT) * (lx * cfg[APERTURE]) + cfg3(cfg, UP) * (ly * cfg[APERTURE])
    return Ray(lens, normalize(focus_point - lens))


@func
def blade_corner(cfg: Buf[f32], k: f32, axis: u32) -> f32:
    """x (axis 0) or y (axis 1) of polygon corner k on the unit circle (rotated by BLADE_ROT)."""
    angle = 2.0 * PI * k / cfg[BLADES] + cfg[BLADE_ROT]
    return cos(angle) if axis == 0 else sin(angle)


@func
def lens_point(cfg: Buf[f32], u1: f32, u2: f32, axis: u32) -> f32:
    """A uniform point on the aperture (unit radius): a disc, or a regular polygon with BLADES sides."""
    if cfg[BLADES] < 3.0:
        r = sqrt(u1)
        phi = 2.0 * PI * u2
        return r * cos(phi) if axis == 0 else r * sin(phi)
    pick = u1 * cfg[BLADES]
    k = floor(pick)
    su = sqrt(pick - k)  # uniform in the triangle (centre, corner k, corner k + 1)
    return blade_corner(cfg, k, axis) * (su * (1.0 - u2)) + blade_corner(cfg, k + 1.0, axis) * (su * u2)


@func
def lens_x(cfg: Buf[f32], u1: f32, u2: f32) -> f32:
    return lens_point(cfg, u1, u2, u32(0))


@func
def lens_y(cfg: Buf[f32], u1: f32, u2: f32) -> f32:
    return lens_point(cfg, u1, u2, u32(1))
