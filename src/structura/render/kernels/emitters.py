"""Emissive primitives as lights (docs/10 §4; host side: render/emitters.py): choose one by power, sample a
point on it (spheres by solid angle, box faces and triangles by area) and report the solid-angle pdf, so the
path tracer can weight light and BSDF sampling with MIS. ``emitter_pdf`` gives the same density for a point
a BSDF ray happened to hit.
"""

from __future__ import annotations

from structura.kernels.skl import PI, Buf, abs, cross, dot, f32, func, length, max, normalize, sqrt, struct, u32, vec3

from .buffers import SceneBufs
from .layout import E_AREA, E_GEO, E_KIND, E_RADIANCE, E_SELECT, EMIT_F, N_EMITTERS, NO_EMITTER
from .sampling import cone_direction


@struct
class EmitSample:
    d: vec3  # unit direction towards the sampled point
    dist: f32
    radiance: vec3
    pdf: f32  # solid angle, including the probability of choosing the emitter (0: nothing sampled)


@func
def ef3(emit_f: Buf[f32], at: u32) -> vec3:
    return vec3(emit_f[at], emit_f[at + 1], emit_f[at + 2])


@func
def emit_search(emit_f: Buf[f32], base: u32, n: u32, u: f32) -> u32:
    """Binary search of the selection CDF stored after the records (a twin of cdf_search: buffer parameters
    keep the buffer's name)."""
    lo = u32(0)
    hi = n
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if emit_f[base + mid] <= u:
            lo = mid
        else:
            hi = mid
    return lo


@func
def no_sample() -> EmitSample:
    return EmitSample(vec3(0.0, 0.0, 1.0), 0.0, vec3(0.0), 0.0)


@func
def cone_pdf(centre: vec3, radius: f32, p: vec3) -> f32:
    """1 / solid angle of the sphere seen from p (0 when p is inside)."""
    dc2 = dot(centre - p, centre - p)
    if dc2 <= radius * radius:
        return 0.0
    cos_max = sqrt(max(0.0, 1.0 - radius * radius / dc2))
    return 1.0 / (2.0 * PI * max(1.0 - cos_max, 1.0e-7))


@func
def sphere_emit(sc: SceneBufs, b: u32, p: vec3, u1: f32, u2: f32) -> EmitSample:
    centre = ef3(sc.emit_f, b + E_GEO)
    radius = sc.emit_f[b + E_GEO + 3]
    pdf = cone_pdf(centre, radius, p)
    if pdf <= 0.0:
        return no_sample()
    to_c = centre - p
    dc2 = dot(to_c, to_c)
    d = cone_direction(normalize(to_c), sqrt(max(0.0, 1.0 - radius * radius / dc2)), u1, u2)
    tc = dot(to_c, d)
    t = tc - sqrt(max(radius * radius - (dc2 - tc * tc), 0.0))
    return EmitSample(d, t, ef3(sc.emit_f, b + E_RADIANCE), pdf)


@func
def area_sample(sc: SceneBufs, b: u32, p: vec3, q: vec3, n_out: vec3, two_sided: bool) -> EmitSample:
    """The sample towards point q on a planar emitter with outward normal n_out (pdf by area → solid angle)."""
    to_l = q - p
    dist = max(length(to_l), 1.0e-6)
    d = to_l * (1.0 / dist)
    cos_l = dot(d * -1.0, n_out)
    if two_sided:
        cos_l = abs(cos_l)
    if cos_l <= 1.0e-6:
        return no_sample()
    return EmitSample(d, dist, ef3(sc.emit_f, b + E_RADIANCE), dist * dist / (cos_l * sc.emit_f[b + E_AREA]))


@func
def box_emit(sc: SceneBufs, b: u32, p: vec3, u1: f32, u2: f32) -> EmitSample:
    """A face chosen by area (each pair of opposite faces shares its weight), then a uniform point on it."""
    corner = ef3(sc.emit_f, b + E_GEO)
    ea = ef3(sc.emit_f, b + E_GEO + 3)
    eb = ef3(sc.emit_f, b + E_GEO + 6)
    ec = ef3(sc.emit_f, b + E_GEO + 9)
    area_a = length(cross(eb, ec))
    area_b = length(cross(ec, ea))
    area_c = length(cross(ea, eb))
    x = u1 * (area_a + area_b + area_c)
    e1 = eb
    e2 = ec
    axis = ea
    r = x / max(area_a, 1.0e-30)
    if x >= area_a + area_b:
        e1 = ea
        e2 = eb
        axis = ec
        r = (x - area_a - area_b) / max(area_c, 1.0e-30)
    elif x >= area_a:
        e1 = ec
        e2 = ea
        axis = eb
        r = (x - area_a) / max(area_b, 1.0e-30)
    n = normalize(cross(e1, e2))
    n = n if dot(n, axis) > 0.0 else n * -1.0  # outward on the far face
    origin = corner + axis
    if r < 0.5:  # the near face: its outward normal points the other way
        origin = corner
        n = n * -1.0
    frac = r * 2.0 if r < 0.5 else r * 2.0 - 1.0
    return area_sample(sc, b, p, origin + e1 * frac + e2 * u2, n, False)


@func
def triangle_emit(sc: SceneBufs, b: u32, p: vec3, u1: f32, u2: f32) -> EmitSample:
    p0 = ef3(sc.emit_f, b + E_GEO)
    e1 = ef3(sc.emit_f, b + E_GEO + 3)
    e2 = ef3(sc.emit_f, b + E_GEO + 6)
    su = sqrt(u1)
    q = p0 + e1 * (su * (1.0 - u2)) + e2 * (su * u2)
    return area_sample(sc, b, p, q, normalize(cross(e1, e2)), True)


@func
def sample_emitter(sc: SceneBufs, p: vec3, u_select: f32, u1: f32, u2: f32) -> EmitSample:
    count = u32(sc.cfg[N_EMITTERS])
    index = emit_search(sc.emit_f, count * u32(EMIT_F), count, u_select)
    b = index * EMIT_F
    es = no_sample()
    kind = sc.emit_f[b + E_KIND]
    if kind == 0.0:
        es = sphere_emit(sc, b, p, u1, u2)
    elif kind == 1.0:
        es = box_emit(sc, b, p, u1, u2)
    else:
        es = triangle_emit(sc, b, p, u1, u2)
    return EmitSample(es.d, es.dist, es.radiance, es.pdf * sc.emit_f[b + E_SELECT])


@func
def emitter_pdf(sc: SceneBufs, prim: u32, origin: vec3, d: vec3, t: f32, normal: vec3) -> f32:
    """The NEE density (solid angle, incl. selection) of the point a ray from origin hit at distance t."""
    index = sc.prim_emit[prim]
    if index == u32(NO_EMITTER):
        return 0.0
    b = index * EMIT_F
    select = sc.emit_f[b + E_SELECT]
    if sc.emit_f[b + E_KIND] == 0.0:
        return select * cone_pdf(ef3(sc.emit_f, b + E_GEO), sc.emit_f[b + E_GEO + 3], origin)
    cos_l = max(abs(dot(d, normal)), 1.0e-6)
    return select * t * t / (cos_l * sc.emit_f[b + E_AREA])
