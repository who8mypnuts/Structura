"""Photon-mapped caustics (docs/10 §2.5; Sunflow's CausticPhotonMap, Jensen's caustic map).

Photons leave the sun through a disc that covers the scene, pass through *specular* surfaces (glass, mirrors,
polished metal; ``is_specular``) by sampling their BSDF, and are stored at the first other surface they reach
after at least one specular bounce. The path integrator then adds the photon estimate at every non-specular
vertex and drops the sunlight it would reach through a specular chain after a non-specular bounce, so each
caustic path is counted once. Photons live in a hash grid of cells twice the gather radius wide: a gather
visits the (up to) eight cells its sphere overlaps, each bucket once.
"""

from __future__ import annotations

from structura.kernels.skl import INF, PI, Buf, BufRW, cos, f32, floor, func, kernel, local, sin, sqrt, u32, uvec3, vec3

from .bsdf import Principled, bsdf_eval, bsdf_sample, principled_setup
from .buffers import SceneBufs
from .camera import cfg3
from .layout import (
    EPS,
    M_METALLIC,
    M_ROUGHNESS,
    M_TRANSMISSION,
    PHOTON_CENTRE,
    PHOTON_COUNT,
    PHOTON_EXTENT,
    PHOTON_F,
    PHOTON_OUT,
    PHOTON_RADIUS,
    PHOTON_TABLE,
    PHOTONS_ON,
    SUN_COS,
    SUN_DIR,
    SUN_IRRADIANCE,
)
from .lights import offset
from .sampling import cone_direction, hash_u32, orthonormal_u, orthonormal_v, rand01, to_local, to_world
from .scene import NO_HIT, trace
from .surface import surface_at, tangent_angle
from .volume import exit_absorption

CELL_OFFSET = 1048576.0  # keeps cell indices positive (|cell| < 2^20)
MAX_BOUNCES = 8


@func
def is_specular(mat_f: Buf[f32], mat: u32) -> bool:
    """Surfaces photons pass through and paths treat as caustic carriers."""
    if mat_f[mat + M_TRANSMISSION] > 0.5:
        return True
    return mat_f[mat + M_ROUGHNESS] < 0.05 or (mat_f[mat + M_METALLIC] > 0.5 and mat_f[mat + M_ROUGHNESS] < 0.25)


@func
def photon_bucket(ix: u32, iy: u32, iz: u32, table: u32) -> u32:
    return hash_u32(ix * u32(73856093) ^ hash_u32(iy * u32(19349663) ^ hash_u32(iz * u32(83492791)))) & (table - 1)


@func
def bucket_light(sc: SceneBufs, bs: Principled, wo: vec3, p: vec3, n: vec3, bucket: u32) -> vec3:
    """The photons of one bucket within the gather radius, weighted by a cone filter and the BSDF."""
    r = sc.cfg[PHOTON_RADIUS]
    base = u32(sc.cfg[PHOTON_TABLE]) * 2
    start = u32(sc.photon_f[bucket * 2])
    total = vec3(0.0)
    for k in range(u32(sc.photon_f[bucket * 2 + 1])):
        q = base + (start + k) * PHOTON_F
        delta = vec3(sc.photon_f[q], sc.photon_f[q + 1], sc.photon_f[q + 2]) - p
        dist2 = delta.x * delta.x + delta.y * delta.y + delta.z * delta.z
        wi = to_local(vec3(sc.photon_f[q + 6], sc.photon_f[q + 7], sc.photon_f[q + 8]), n)
        if dist2 < r * r and wi.z > 0.0:
            v = bsdf_eval(bs, wo, wi)
            flux = vec3(sc.photon_f[q + 3], sc.photon_f[q + 4], sc.photon_f[q + 5])
            total = total + v.f * flux * ((1.0 - sqrt(dist2) / r) * 3.0 / (PI * r * r * wi.z))
    return total


@func
def caustic_light(sc: SceneBufs, bs: Principled, wo: vec3, p: vec3, n: vec3) -> vec3:
    """Radiance towards wo from the caustic photons around p (0 without a photon map)."""
    if sc.cfg[PHOTONS_ON] == 0.0:
        return vec3(0.0)
    r = sc.cfg[PHOTON_RADIUS]
    table = u32(sc.cfg[PHOTON_TABLE])
    corner = vec3(floor((p.x - r) / (2.0 * r)), floor((p.y - r) / (2.0 * r)), floor((p.z - r) / (2.0 * r)))
    seen = local(u32, 8)
    n_seen = u32(0)
    total = vec3(0.0)
    for c in range(8):
        ix = u32(corner.x + f32(c & u32(1)) + CELL_OFFSET)
        iy = u32(corner.y + f32((c >> u32(1)) & u32(1)) + CELL_OFFSET)
        iz = u32(corner.z + f32((c >> u32(2)) & u32(1)) + CELL_OFFSET)
        bucket = photon_bucket(ix, iy, iz, table)
        fresh = True
        for k in range(n_seen):
            fresh = fresh and seen[k] != bucket
        if fresh:
            seen[n_seen] = bucket
            n_seen += 1
            total = total + bucket_light(sc, bs, wo, p, n, bucket)
    return total


@func
def sun_photon_origin(sc: SceneBufs, i: u32, seed: u32) -> vec3:
    """A point on the disc that faces the sun and covers the scene's bounding sphere, outside the scene."""
    sun = cfg3(sc.cfg, SUN_DIR)
    radius = sc.cfg[PHOTON_EXTENT]
    rr = radius * sqrt(rand01(i, seed, u32(0)))
    phi = 2.0 * PI * rand01(i, seed, u32(1))
    disc = orthonormal_u(sun) * (rr * cos(phi)) + orthonormal_v(sun) * (rr * sin(phi))
    return cfg3(sc.cfg, PHOTON_CENTRE) + sun * (radius * 2.0) + disc


@kernel(workgroup=(64, 1, 1))
def photon_pass(gid: uvec3, count: u32, seed: u32, sc: SceneBufs, photons: BufRW[f32]) -> None:
    """Trace one sun photon; store it at the first non-specular surface after a specular bounce."""
    i = gid.x
    if i >= count:
        return
    at = i * PHOTON_OUT
    photons[at + 9] = 0.0
    radius = sc.cfg[PHOTON_EXTENT]
    flux = cfg3(sc.cfg, SUN_IRRADIANCE) * (PI * radius * radius / sc.cfg[PHOTON_COUNT])
    o = sun_photon_origin(sc, i, seed)
    d = cone_direction(cfg3(sc.cfg, SUN_DIR), sc.cfg[SUN_COS], rand01(i, seed, u32(2)), rand01(i, seed, u32(3)))
    d = d * -1.0
    for bounce in range(MAX_BOUNCES):
        h = trace(o, d, 0.0, INF, u32(0), u32(NO_HIT), sc)
        if h.prim == NO_HIT:
            return
        flux = flux * exit_absorption(sc.mat_f, sc.prim_u, h.prim, h.front, h.t)
        s = surface_at(sc, h.prim)
        p = o + d * h.t
        if not is_specular(sc.mat_f, s.mat):
            if bounce > 0:
                store_photon(photons, at, p, flux, d * -1.0)
            return
        wo = to_local(d * -1.0, h.normal)
        bs = principled_setup(sc.mat_f, s, wo, h.front, 0.0, tangent_angle(sc, h.prim, s.mat, h.normal))
        dim = u32(4) + u32(bounce) * 3
        wi = bsdf_sample(bs, wo, rand01(i, seed, dim), rand01(i, seed, dim + 1), rand01(i, seed, dim + 2))
        v = bsdf_eval(bs, wo, wi)
        if v.pdf <= 0.0:
            return
        flux = flux * v.f * (1.0 / v.pdf)
        o = offset(p, h.normal if wi.z > 0.0 else h.normal * -1.0, sc.cfg[EPS])
        d = to_world(wi, h.normal)


@func
def store_photon(photons: BufRW[f32], at: u32, p: vec3, flux: vec3, towards: vec3) -> None:
    photons[at] = p.x
    photons[at + 1] = p.y
    photons[at + 2] = p.z
    photons[at + 3] = flux.x
    photons[at + 4] = flux.y
    photons[at + 5] = flux.z
    photons[at + 6] = towards.x
    photons[at + 7] = towards.y
    photons[at + 8] = towards.z
    photons[at + 9] = 1.0
