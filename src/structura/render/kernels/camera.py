"""Camera rays, configured through the cfg buffer (render/lens_config.py): perspective with a thin lens (disc or
polygonal aperture, bokeh bias, anamorphic stretch, lens shift and a tiltable focus plane), orthographic,
spherical, and fisheye with three angle mappings."""

from __future__ import annotations

from structura.kernels.skl import (
    PI,
    Buf,
    asin,
    atan,
    clamp,
    cos,
    dot,
    f32,
    floor,
    func,
    max,
    normalize,
    pow,
    sin,
    sqrt,
    struct,
    tan,
    u32,
    vec3,
)

from .layout import (
    ANAMORPHIC,
    APERTURE,
    ASPECT,
    BLADE_ROT,
    BLADES,
    BOKEH_BIAS,
    CAM_TYPE,
    EYE,
    FISHEYE_FOV,
    FISHEYE_MAP,
    FOCUS,
    FOCUS_NORMAL,
    FORWARD,
    ORTHO_HALF,
    RIGHT,
    SHIFT,
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
    """Returns a spherical (equirectangular 360°) or fisheye ray around the camera basis.

    Args:
        cfg: The render configuration.
        sx: Screen x in -1..1.
        sy: Screen y in -1..1 (up).
    """
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
    angle = fisheye_angle(cfg, radius)
    s = sin(angle) / max(radius, 1.0e-6)
    return Ray(cfg3(cfg, EYE), normalize(f * cos(angle) + r * (px * s) + u * (sy * s)))


@func
def fisheye_angle(cfg: Buf[f32], radius: f32) -> f32:
    """Returns the angle off the view axis at a distance from the image centre.

    Args:
        cfg: The render configuration (field of view and mapping).
        radius: Distance from the centre; 1 is the top of the frame, which sees half the field of view.
    """
    half_field = 0.5 * cfg[FISHEYE_FOV]
    if cfg[FISHEYE_MAP] == 1.0:  # equisolid: r ∝ sin(θ/2)
        return 2.0 * asin(clamp(radius * sin(0.5 * half_field), -1.0, 1.0))
    if cfg[FISHEYE_MAP] == 2.0:  # stereographic: r ∝ tan(θ/2)
        return 2.0 * atan(radius * tan(0.5 * half_field))
    return radius * half_field  # equidistant


@func
def camera_ray(cfg: Buf[f32], sx: f32, sy: f32, u1: f32, u2: f32) -> Ray:
    """Returns the ray through a screen position, sampling the lens for depth of field.

    Args:
        cfg: The render configuration (camera basis, projection, shift, lens).
        sx: Screen x in -1..1.
        sy: Screen y in -1..1 (up).
        u1: A uniform random number for the lens.
        u2: Another uniform random number for the lens.
    """
    if cfg[CAM_TYPE] >= 2.0:
        return panoramic_ray(cfg, sx, sy)
    px = sx * cfg[ASPECT] + 2.0 * cfg[SHIFT]  # lens shift, in frame heights (2 = the frame's full height)
    py = sy + 2.0 * cfg[SHIFT + 1]
    if cfg[CAM_TYPE] == 1.0:
        offset = cfg3(cfg, RIGHT) * (px * cfg[ORTHO_HALF]) + cfg3(cfg, UP) * (py * cfg[ORTHO_HALF])
        return Ray(cfg3(cfg, EYE) + offset, cfg3(cfg, FORWARD))
    eye = cfg3(cfg, EYE)
    d = normalize(cfg3(cfg, FORWARD) + cfg3(cfg, RIGHT) * (px * cfg[TAN_HALF]) + cfg3(cfg, UP) * (py * cfg[TAN_HALF]))
    if cfg[APERTURE] <= 0.0:
        return Ray(eye, d)
    n = cfg3(cfg, FOCUS_NORMAL)  # the focus plane: through eye + forward · FOCUS, tilted by the lens
    focus_point = eye + d * (cfg[FOCUS] * dot(cfg3(cfg, FORWARD), n) / max(1.0e-6, dot(d, n)))
    lx = lens_x(cfg, u1, u2) * cfg[ANAMORPHIC]
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
    """Returns one coordinate of a point on the unit aperture: a disc, or a polygon with BLADES sides.

    The radial exponent BOKEH_BIAS is 0.5 for an evenly lit aperture (smaller: bright rims; larger: a soft
    centre).

    Args:
        cfg: The render configuration.
        u1: A uniform random number.
        u2: Another uniform random number.
        axis: 0 for x, 1 for y.
    """
    if cfg[BLADES] < 3.0:
        r = pow(max(u1, 1.0e-12), cfg[BOKEH_BIAS])
        phi = 2.0 * PI * u2
        return r * cos(phi) if axis == 0 else r * sin(phi)
    pick = u1 * cfg[BLADES]
    k = floor(pick)
    su = pow(max(pick - k, 1.0e-12), cfg[BOKEH_BIAS])  # 0.5: uniform in the triangle (centre, corner k, k + 1)
    return blade_corner(cfg, k, axis) * (su * (1.0 - u2)) + blade_corner(cfg, k + 1.0, axis) * (su * u2)


@func
def lens_x(cfg: Buf[f32], u1: f32, u2: f32) -> f32:
    return lens_point(cfg, u1, u2, u32(0))


@func
def lens_y(cfg: Buf[f32], u1: f32, u2: f32) -> f32:
    return lens_point(cfg, u1, u2, u32(1))
