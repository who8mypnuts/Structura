"""'path': unidirectional path tracing with sun next-event estimation + MIS (docs/10 §2.3, R1 subset).

Stochastic opacity passes through an instance (the same single-crossing semantics as Structure Synth);
camera rays that only pass through or refract keep seeing the backdrop colour, everything else sees the sky.
"""

from __future__ import annotations

from structura.kernels.skl import INF, Buf, dot, f32, func, max3, min, normalize, struct, u32, vec3

from .bsdf import Principled, bsdf_eval, bsdf_sample, principled_setup
from .buffers import SceneBufs
from .camera import cfg3
from .catcher import shadow_ratio
from .emitters import emitter_pdf, sample_emitter
from .environment import env_pdf, env_radiance, env_sample
from .fog import fog_light, fog_transmittance
from .layout import (
    BACKDROP_SKY,
    BACKGROUND,
    CAUSTIC_ALPHA,
    DIFFUSE_BOUNCES,
    ENV_ON,
    EPS,
    GLOSSY_BOUNCES,
    M_MODEL,
    MODEL_CATCHER,
    MODEL_CONSTANT,
    N_EMITTERS,
    N_LIGHTS,
    PHOTONS_ON,
    SUN_COS,
    SUN_DIR,
    SUN_IRRADIANCE,
    TRANSMISSION_BOUNCES,
)
from .lights import light_sample, offset, power_heuristic, sun_pdf, sun_radiance, unoccluded
from .microfacet import luminance
from .models import is_special, special_radiance
from .photons import caustic_light, is_specular
from .sampling import cone_direction, sample01, to_local, to_world
from .scene import NO_HIT, PRIM_U, Hit, trace
from .surface import Surface, surface_at, tangent_angle
from .volume import exit_absorption

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
def env_nee(sc: SceneBufs, bs: Principled, wo: vec3, p: vec3, n: vec3, u1: f32, u2: f32) -> vec3:
    """Light from the environment map, importance-sampled and weighted against BSDF sampling."""
    if sc.cfg[ENV_ON] == 0.0:
        return vec3(0.0)
    es = env_sample(sc, u1, u2)
    if es.pdf <= 0.0:
        return vec3(0.0)
    wi = to_local(es.d, n)
    v = bsdf_eval(bs, wo, wi)
    if luminance(v.f) <= 0.0:
        return vec3(0.0)
    side = n if wi.z > 0.0 else n * -1.0
    if not unoccluded(sc, p, side, es.d, INF):
        return vec3(0.0)
    return v.f * es.radiance * (power_heuristic(es.pdf, v.pdf) / es.pdf)


@func
def emitter_nee(sc: SceneBufs, bs: Principled, wo: vec3, p: vec3, n: vec3, u: vec3) -> vec3:
    """Light from one emissive primitive chosen by power (u: selection, then two sample coordinates)."""
    if sc.cfg[N_EMITTERS] == 0.0:
        return vec3(0.0)
    es = sample_emitter(sc, p, u.x, u.y, u.z)
    if es.pdf <= 0.0:
        return vec3(0.0)
    wi = to_local(es.d, n)
    v = bsdf_eval(bs, wo, wi)
    if luminance(v.f) <= 0.0:
        return vec3(0.0)
    side = n if wi.z > 0.0 else n * -1.0
    if not unoccluded(sc, p, side, es.d, es.dist * 0.999):
        return vec3(0.0)
    return v.f * es.radiance * (power_heuristic(es.pdf, v.pdf) / es.pdf)


@func
def emission_weight(sc: SceneBufs, h: Hit, origin: vec3, d: vec3, last_pdf: f32) -> f32:
    """MIS weight of emission reached by BSDF sampling (1 for camera rays and non-emitters)."""
    if last_pdf <= 0.0 or sc.cfg[N_EMITTERS] == 0.0:
        return 1.0
    light_pdf = emitter_pdf(sc, h.prim, origin, d, h.t, h.normal)
    return power_heuristic(last_pdf, light_pdf) if light_pdf > 0.0 else 1.0


@func
def escaped(sc: SceneBufs, d: vec3, backdrop: bool, last_pdf: f32, photon_mapped: bool) -> vec3:
    """Sky and sun along an escaped ray; ``photon_mapped``: its sunlight is in the caustic photon map."""
    if backdrop and sc.cfg[BACKDROP_SKY] == 0.0:
        return cfg3(sc.cfg, BACKGROUND)
    sun = sun_radiance(sc.cfg, d) * (0.0 if photon_mapped else 1.0)
    weight = power_heuristic(last_pdf, sun_pdf(sc.cfg)) if last_pdf > 0.0 else 1.0
    env_weight = 1.0
    if sc.cfg[ENV_ON] != 0.0 and last_pdf > 0.0:  # the map was also light-sampled at the last vertex
        env_weight = power_heuristic(last_pdf, env_pdf(sc, d))
    return env_radiance(sc, d) * env_weight + sun * weight


@func
def caught(sc: SceneBufs, rd: vec3, p: vec3, n: vec3, pixel: u32, sample_index: u32, dim: u32) -> vec3:
    """What a camera ray sees at a shadow catcher: the backdrop behind it, darkened by the scene's shadows."""
    return escaped(sc, rd, True, 0.0, False) * shadow_ratio(sc, p, n, pixel, sample_index, dim)


@func
def surface_light(sc: SceneBufs, s: Surface, h: Hit, origin: vec3, d: vec3, last_pdf: f32) -> vec3:
    """Emission (MIS-weighted), plus the flat colour of the 'constant' model."""
    unlit = s.base if sc.mat_f[s.mat + M_MODEL] == f32(MODEL_CONSTANT) else vec3(0.0)
    return s.emission * emission_weight(sc, h, origin, d, last_pdf) + unlit


@func
def caustic_state(sc: SceneBufs, mat: u32, state: f32) -> f32:
    """0: no photon map or nothing yet; 1: a non-specular bounce happened; 2: leaving a specular surface after
    one — the sunlight such a path reaches is already in the photon map."""
    if sc.cfg[PHOTONS_ON] == 0.0:
        return 0.0
    if not is_specular(sc.mat_f, mat):
        return 1.0
    return 2.0 if state >= 1.0 else 0.0


@func
def roulette(depth: u32, throughput: vec3, u: f32) -> f32:
    """Russian roulette from the third bounce: 0 ends the path, else the throughput scale 1/q."""
    if depth < 3:
        return 1.0
    q = min(0.95, max3(throughput))
    return 0.0 if u > q else 1.0 / q


@func
def ends_here(sc: SceneBufs, mat: u32, backdrop: bool) -> bool:
    """Returns whether a path stops at a surface: a shadow catcher seen directly, or a special (unlit) model.

    Args:
        sc: The scene buffers.
        mat: Offset of the surface's material record.
        backdrop: True while the path is still the camera ray (or passed only through see-through instances).
    """
    return (backdrop and sc.mat_f[mat + M_MODEL] == f32(MODEL_CATCHER)) or is_special(sc.mat_f, mat)


@func
def terminal_light(
    sc: SceneBufs, h: Hit, s: Surface, p: vec3, rd: vec3, pixel: u32, sample_index: u32, dim: u32
) -> vec3:
    """Returns what a path that ``ends_here`` sees.

    Args:
        sc: The scene buffers.
        h: The hit.
        s: The surface at the hit.
        p: The hit point.
        rd: The ray direction.
        pixel: The pixel (random-number stream).
        sample_index: The sample (random-number stream).
        dim: The first random dimension this function may use.

    Returns:
        The backdrop darkened by the shadows on a catcher, or the special model's colour.
    """
    if sc.mat_f[s.mat + M_MODEL] == f32(MODEL_CATCHER):
        return caught(sc, rd, p, h.normal, pixel, sample_index, dim + 13)
    return special_radiance(sc, h, p, rd, s, pixel, sample_index, dim + 14)


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
    """Samples the direct light at a path vertex and one BSDF-sampled continuation.

    Args:
        sc: The scene buffers.
        h: The hit.
        s: The surface at the hit.
        p: The hit point.
        rd: The incoming ray direction.
        alpha_floor: Roughness floor of the glossy lobes (filtered caustics).
        pixel: The pixel (random-number stream).
        sample_index: The sample (random-number stream).
        dim: The first random dimension this function may use.

    Returns:
        The direct light and the continuation (a zero weight ends the path).
    """
    wo = to_local(rd * -1.0, h.normal)
    bs = principled_setup(sc.mat_f, s, wo, h.front, alpha_floor, tangent_angle(sc, h.prim, s.mat, h.normal))
    u1 = sample01(sc.cfg, pixel, sample_index, dim)
    u2 = sample01(sc.cfg, pixel, sample_index, dim + 1)
    direct = sun_nee(sc, bs, wo, p, h.normal, u1, u2) + lights_nee(sc, bs, wo, p, h.normal, u1, u2)
    u_env = sample01(sc.cfg, pixel, sample_index, dim + 8)
    u_env2 = sample01(sc.cfg, pixel, sample_index, dim + 9)
    direct = direct + env_nee(sc, bs, wo, p, h.normal, u_env, u_env2)
    u_emit = vec3(sample01(sc.cfg, pixel, sample_index, dim + 10), sample01(sc.cfg, pixel, sample_index, dim + 11),
                  sample01(sc.cfg, pixel, sample_index, dim + 12))  # fmt: skip
    direct = direct + emitter_nee(sc, bs, wo, p, h.normal, u_emit)
    if not is_specular(sc.mat_f, s.mat):
        direct = direct + caustic_light(sc, bs, wo, p, h.normal)
    u_lobe = sample01(sc.cfg, pixel, sample_index, dim + 2)
    u_dir = sample01(sc.cfg, pixel, sample_index, dim + 3)
    wi = bsdf_sample(bs, wo, u_lobe, u_dir, sample01(sc.cfg, pixel, sample_index, dim + 4))
    v = bsdf_eval(bs, wo, wi)
    if v.pdf <= 0.0 or luminance(v.f) <= 0.0:
        return Scatter(direct, vec3(0.0), p, rd, 0.0)
    side = h.normal if wi.z > 0.0 else h.normal * -1.0
    return Scatter(direct, v.f * (1.0 / v.pdf), offset(p, side, sc.cfg[EPS]), normalize(to_world(wi, h.normal)), v.pdf)


@func
def lobe_of(sca: Scatter, n: vec3, rd: vec3) -> vec3:
    """The bounce as a count vector: (1,0,0) diffuse-like, (0,1,0) glossy, (0,0,1) transmission."""
    if dot(sca.d, n) * dot(rd, n) > 0.0:  # continues to the other side of the surface
        return vec3(0.0, 0.0, 1.0)
    return vec3(1.0, 0.0, 0.0) if sca.pdf < ROUGH_PDF else vec3(0.0, 1.0, 0.0)


@func
def bounces(lobes: vec3) -> u32:
    return u32(lobes.x + lobes.y + lobes.z + 0.5)


@func
def within_lobe_limits(cfg: Buf[f32], lobes: vec3) -> bool:
    return lobes.x <= cfg[DIFFUSE_BOUNCES] and lobes.y <= cfg[GLOSSY_BOUNCES] and lobes.z <= cfg[TRANSMISSION_BOUNCES]


@func
def path_radiance(o: vec3, d: vec3, max_bounces: u32, pixel: u32, sample_index: u32, sc: SceneBufs) -> vec3:
    """Returns the radiance along a camera ray: the path tracer.

    Args:
        o: The ray origin.
        d: The ray direction.
        max_bounces: The longest path (see-through passes do not count).
        pixel: The pixel (random-number stream).
        sample_index: The sample (random-number stream).
        sc: The scene buffers.
    """
    radiance = vec3(0.0)
    throughput = vec3(1.0)
    ro = o
    rd = d
    exclude = u32(NO_HIT)
    backdrop = True
    last_pdf = 0.0
    alpha_floor = 0.0
    caustic = 0.0  # photon-map state (caustic_state): 2 = in a specular chain after a non-specular bounce
    lobes = vec3(0.0)  # diffuse, glossy and transmission bounces so far (per-lobe limits)
    for step in range(max_bounces + PASS_LIMIT):
        h = trace(ro, rd, 0.0, INF, u32(0), exclude, sc)
        radiance = radiance + throughput * fog_light(sc.cfg, ro, rd, h.t)
        throughput = throughput * fog_transmittance(sc.cfg, ro, rd, h.t)
        if h.prim == NO_HIT:
            radiance = radiance + throughput * escaped(sc, rd, backdrop, last_pdf, caustic == 2.0)
            break
        throughput = throughput * exit_absorption(sc.mat_f, sc.prim_u, h.prim, h.front, h.t)  # inside glass
        dim = u32(32) + u32(step) * 16
        s = surface_at(sc, h.prim)
        p = ro + rd * h.t
        if s.alpha < 1.0 and sample01(sc.cfg, pixel, sample_index, dim + 7) >= s.alpha:
            ro = p
            exclude = sc.prim_u[h.prim * PRIM_U + 2]
            continue
        exclude = u32(NO_HIT)
        if ends_here(sc, s.mat, backdrop):  # a shadow catcher seen directly, or wireframe / ao / a debug view
            radiance = radiance + throughput * terminal_light(sc, h, s, p, rd, pixel, sample_index, dim)
            break
        radiance = radiance + throughput * surface_light(sc, s, h, ro, rd, last_pdf)
        if sc.mat_f[s.mat + M_MODEL] == f32(MODEL_CONSTANT) or bounces(lobes) >= max_bounces:
            break
        sca = scatter(sc, h, s, p, rd, alpha_floor, pixel, sample_index, dim)
        radiance = radiance + throughput * sca.direct
        lobes = lobes + lobe_of(sca, h.normal, rd)
        if sca.pdf <= 0.0 or not within_lobe_limits(sc.cfg, lobes):
            break
        throughput = throughput * sca.weight
        last_pdf = sca.pdf
        alpha_floor = sc.cfg[CAUSTIC_ALPHA] if sca.pdf < ROUGH_PDF else alpha_floor
        caustic = caustic_state(sc, s.mat, caustic)
        backdrop = backdrop and dot(sca.d, h.normal) < 0.0
        ro = sca.o
        rd = sca.d
        keep = roulette(bounces(lobes), throughput, sample01(sc.cfg, pixel, sample_index, dim + 5))
        throughput = throughput * keep
        if keep == 0.0:
            break
    return radiance
