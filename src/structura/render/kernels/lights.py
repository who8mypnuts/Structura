"""Environment and sun (docs/10 §4, R1): gradient sky + a sun disc sampled by cone, combined with MIS."""

from __future__ import annotations

from structura.kernels.skl import (
    PI,
    Buf,
    abs,
    clamp,
    cross,
    dot,
    f32,
    func,
    length,
    max,
    mix,
    normalize,
    struct,
    u32,
    vec3,
)

from .buffers import SceneBufs
from .camera import cfg3
from .layout import (
    EPS,
    L_COS_INNER,
    L_COS_OUTER,
    L_DIR,
    L_EDGE_V,
    L_INTENSITY,
    L_POS,
    L_RADIUS,
    L_TYPE,
    LIGHT_F,
    SKY_BOTTOM,
    SKY_TOP,
    SUN_COS,
    SUN_DIR,
    SUN_IRRADIANCE,
)
from .sampling import cone_direction
from .scene import NO_HIT, TRACE_ANY, trace

INF_DIST = 3.0e38


@func
def offset(p: vec3, n: vec3, eps: f32) -> vec3:
    """Move a surface point off the surface along n (scale-aware epsilon)."""
    scale = 1.0 + max(abs(p.x), max(abs(p.y), abs(p.z)))
    return p + n * (eps * scale)


@func
def sky(cfg: Buf[f32], d: vec3) -> vec3:
    return mix(cfg3(cfg, SKY_BOTTOM), cfg3(cfg, SKY_TOP), clamp(d.y * 0.5 + 0.5, 0.0, 1.0))


@func
def sun_pdf(cfg: Buf[f32]) -> f32:
    """Solid-angle pdf of uniform cone sampling over the sun disc (1 / Ω)."""
    return 1.0 / (2.0 * PI * max(1.0 - cfg[SUN_COS], 1.0e-7))


@func
def sun_radiance(cfg: Buf[f32], d: vec3) -> vec3:
    """Radiance of the sun disc along d (its irradiance spread over the disc's solid angle)."""
    if dot(d, cfg3(cfg, SUN_DIR)) < cfg[SUN_COS]:
        return vec3(0.0)
    return cfg3(cfg, SUN_IRRADIANCE) * sun_pdf(cfg)


@func
def unoccluded(sc: SceneBufs, p: vec3, n: vec3, d: vec3, t_max: f32) -> bool:
    h = trace(offset(p, n, sc.cfg[EPS]), d, 0.0, t_max, u32(TRACE_ANY), u32(NO_HIT), sc)
    return h.prim == u32(NO_HIT)


@func
def power_heuristic(a: f32, b: f32) -> f32:
    a2 = a * a
    return a2 / max(a2 + b * b, 1.0e-30)


@struct
class LightSample:
    d: vec3  # unit direction towards the light
    dist: f32
    irradiance: vec3  # radiant intensity / distance² (× spot falloff)


@func
def rect_sample(sc: SceneBufs, b: u32, p: vec3, u1: f32, u2: f32) -> LightSample:
    """A point on a one-sided rectangular emitter, sampled by area: E = L · cosθ_light · A / d²."""
    centre = vec3(sc.light_f[b + L_POS], sc.light_f[b + L_POS + 1], sc.light_f[b + L_POS + 2])
    eu = vec3(sc.light_f[b + L_DIR], sc.light_f[b + L_DIR + 1], sc.light_f[b + L_DIR + 2])
    ev = vec3(sc.light_f[b + L_EDGE_V], sc.light_f[b + L_EDGE_V + 1], sc.light_f[b + L_EDGE_V + 2])
    q = centre + eu * (2.0 * u1 - 1.0) + ev * (2.0 * u2 - 1.0)
    to_light = q - p
    dist = max(length(to_light), 1.0e-6)
    d = to_light * (1.0 / dist)
    cos_light = dot(d * -1.0, normalize(cross(eu, ev)))
    radiance = vec3(sc.light_f[b + L_INTENSITY], sc.light_f[b + L_INTENSITY + 1], sc.light_f[b + L_INTENSITY + 2])
    if cos_light <= 0.0:
        return LightSample(d, dist, vec3(0.0))
    return LightSample(d, dist, radiance * (cos_light * sc.light_f[b + L_RADIUS] / (dist * dist)))


@func
def light_sample(sc: SceneBufs, index: u32, p: vec3, u1: f32, u2: f32) -> LightSample:
    """Direction, distance and incident radiance × solid-angle factor from one point/sphere/spot/rect light."""
    b = index * LIGHT_F
    if sc.light_f[b + L_TYPE] == 3.0:
        return rect_sample(sc, b, p, u1, u2)
    pos = vec3(sc.light_f[b + L_POS], sc.light_f[b + L_POS + 1], sc.light_f[b + L_POS + 2])
    radius = sc.light_f[b + L_RADIUS]
    if radius > 0.0:  # a sphere light: jitter over the disc facing p (soft shadows)
        axis = normalize(p - pos)
        disc = cone_direction(axis, 0.0, u1, u2)
        pos = pos + disc * radius
    to_light = pos - p
    dist = max(length(to_light), 1.0e-6)
    d = to_light * (1.0 / dist)
    intensity = vec3(sc.light_f[b + L_INTENSITY], sc.light_f[b + L_INTENSITY + 1], sc.light_f[b + L_INTENSITY + 2])
    falloff = 1.0
    if sc.light_f[b + L_TYPE] == 2.0:  # spot: smooth cone
        spot_dir = vec3(sc.light_f[b + L_DIR], sc.light_f[b + L_DIR + 1], sc.light_f[b + L_DIR + 2])
        c = dot(d * -1.0, spot_dir)
        outer = sc.light_f[b + L_COS_OUTER]
        inner = sc.light_f[b + L_COS_INNER]
        falloff = clamp((c - outer) / max(inner - outer, 1.0e-4), 0.0, 1.0)
    return LightSample(d, dist, intensity * (falloff / (dist * dist)))
