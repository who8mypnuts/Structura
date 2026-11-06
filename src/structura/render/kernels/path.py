"""'path': unidirectional path tracing with sun next-event estimation + MIS (docs/10 §2.3, R1 subset).

Stochastic opacity passes through an instance (the same single-crossing semantics as Structure Synth);
camera rays that only pass through or refract keep seeing the backdrop colour, everything else sees the sky.
"""

from __future__ import annotations

from structura.kernels.skl import INF, dot, f32, func, max3, min, normalize, struct, u32, vec3

from .bsdf import Principled, bsdf_eval, bsdf_sample, principled_setup
from .buffers import SceneBufs
from .camera import cfg3
from .layout import BACKDROP_SKY, BACKGROUND, CAUSTIC_ALPHA, EPS, M_MODEL, N_LIGHTS, SUN_COS, SUN_DIR, SUN_IRRADIANCE
from .lights import light_sample, offset, power_heuristic, sky, sun_pdf, sun_radiance, unoccluded
from .microfacet import luminance
from .sampling import cone_direction, rand01, to_local, to_world
from .scene import NO_HIT, PRIM_U, Hit, trace
from .surface import Surface, surface_at

MODEL_CONSTANT = 1
PASS_LIMIT = 16  # extra steps allowed for opacity pass-through
ROUGH_PDF = 2.0  # a sampled pdf below this marks a rough (diffuse-like) bounce


@func
def sun_nee(sc: SceneBufs, bs: Principled, wo: vec3, p: vec3, n: vec3, u1: f32, u2: f32) -> vec3:
    """Direct sunlight: f·cos·E weighted against BSDF sampling of the same disc."""
    ldir = cone_direction(cfg3(sc.cfg, SUN_DIR), sc.cfg[SUN_COS], u1, u2)
    wi = to_local(ldir, n)
    v = bsdf_eval(bs, wo, wi)
    if luminance(v.f) <= 0.0:
        return vec3(0.0)
    side = n if wi.z > 0.0 else n * -1.0
    if not unoccluded(sc, p, side, ldir, INF):
        return vec3(0.0)
    return v.f * cfg3(sc.cfg, SUN_IRRADIANCE) * power_heuristic(sun_pdf(sc.cfg), v.pdf)


@func
def lights_nee(sc: SceneBufs, bs: Principled, wo: vec3, p: vec3, n: vec3, u1: f32, u2: f32) -> vec3:
    """Direct light from every point / sphere / spot light (delta or tiny: no MIS needed)."""
    total = vec3(0.0)
    for i in range(u32(sc.cfg[N_LIGHTS])):
        ls = light_sample(sc, u32(i), p, u1, u2)
        wi = to_local(ls.d, n)
        v = bsdf_eval(bs, wo, wi)
        if luminance(v.f) > 0.0:
            side = n if wi.z > 0.0 else n * -1.0
            if unoccluded(sc, p, side, ls.d, ls.dist * 0.999):
                total = total + v.f * ls.irradiance
    return total


@func
def escaped(sc: SceneBufs, d: vec3, backdrop: bool, last_pdf: f32) -> vec3:
    if backdrop and sc.cfg[BACKDROP_SKY] == 0.0:
        return cfg3(sc.cfg, BACKGROUND)
    sun = sun_radiance(sc.cfg, d)
    weight = power_heuristic(last_pdf, sun_pdf(sc.cfg)) if last_pdf > 0.0 else 1.0
    return sky(sc.cfg, d) + sun * weight


@struct
class Scatter:
    direct: vec3  # sunlight reaching the camera through this vertex (before the path throughput)
    weight: vec3  # f·cos / pdf of the continuation; zero ends the path
    o: vec3
    d: vec3
    pdf: f32


@func
def scatter(
    sc: SceneBufs, h: Hit, s: Surface, p: vec3, rd: vec3, alpha_floor: f32, pixel: u32, sample_index: u32, dim: u32
) -> Scatter:
    """Sun NEE at the vertex plus one BSDF-sampled continuation."""
    wo = to_local(rd * -1.0, h.normal)
    bs = principled_setup(sc.mat_f, s, wo, h.front, alpha_floor)
    u1 = rand01(pixel, sample_index, dim)
    u2 = rand01(pixel, sample_index, dim + 1)
    direct = sun_nee(sc, bs, wo, p, h.normal, u1, u2) + lights_nee(sc, bs, wo, p, h.normal, u1, u2)
    u_lobe = rand01(pixel, sample_index, dim + 2)
    wi = bsdf_sample(bs, wo, u_lobe, rand01(pixel, sample_index, dim + 3), rand01(pixel, sample_index, dim + 4))
    v = bsdf_eval(bs, wo, wi)
    if v.pdf <= 0.0 or luminance(v.f) <= 0.0:
        return Scatter(direct, vec3(0.0), p, rd, 0.0)
    side = h.normal if wi.z > 0.0 else h.normal * -1.0
    return Scatter(direct, v.f * (1.0 / v.pdf), offset(p, side, sc.cfg[EPS]), normalize(to_world(wi, h.normal)), v.pdf)


@func
def path_radiance(o: vec3, d: vec3, max_bounces: u32, pixel: u32, sample_index: u32, sc: SceneBufs) -> vec3:
    radiance = vec3(0.0)
    throughput = vec3(1.0)
    ro = o
    rd = d
    exclude = u32(NO_HIT)
    backdrop = True
    last_pdf = 0.0
    depth = u32(0)
    alpha_floor = 0.0
    for step in range(max_bounces + PASS_LIMIT):
        h = trace(ro, rd, 0.0, INF, u32(0), exclude, sc)
        if h.prim == NO_HIT:
            radiance = radiance + throughput * escaped(sc, rd, backdrop, last_pdf)
            break
        dim = u32(32) + u32(step) * 16
        s = surface_at(sc, h.prim)
        p = ro + rd * h.t
        if s.alpha < 1.0 and rand01(pixel, sample_index, dim + 7) >= s.alpha:
            ro = p
            exclude = sc.prim_u[h.prim * PRIM_U + 2]
            continue
        exclude = u32(NO_HIT)
        radiance = radiance + throughput * s.emission
        if sc.mat_f[s.mat + M_MODEL] == f32(MODEL_CONSTANT):
            radiance = radiance + throughput * s.base
            break
        if depth >= max_bounces:
            break
        sca = scatter(sc, h, s, p, rd, alpha_floor, pixel, sample_index, dim)
        radiance = radiance + throughput * sca.direct
        if sca.pdf <= 0.0:
            break
        throughput = throughput * sca.weight
        last_pdf = sca.pdf
        if sca.pdf < ROUGH_PDF:
            alpha_floor = sc.cfg[CAUSTIC_ALPHA]
        backdrop = backdrop and dot(sca.d, h.normal) < 0.0
        ro = sca.o
        rd = sca.d
        depth += 1
        if depth >= 3:
            q = min(0.95, max3(throughput))
            if rand01(pixel, sample_index, dim + 5) > q:
                break
            throughput = throughput * (1.0 / q)
    return radiance
