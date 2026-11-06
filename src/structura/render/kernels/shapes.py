"""Ray–shape intersections (exact arithmetic: no fast-math contractions). Distances are world-ray parameters."""

from __future__ import annotations

from structura.kernels.skl import INF, abs, cross, dot, f32, func, max3, min3, select, sqrt, struct, vec3


@struct
class Span:
    near: f32
    far: f32


@func(exact=True)
def unit_box_span(o: vec3, inv: vec3) -> Span:
    """Entry/exit parameters of the ray o + t·d (inv = 1/d) with the unit cube [0,1]³ (far < near: miss)."""
    t0 = (vec3(0.0) - o) * inv
    t1 = (vec3(1.0) - o) * inv
    return Span(max3(min(t0, t1)), min3(max(t0, t1)))


@func(exact=True)
def box_face_normal(p: vec3) -> vec3:
    """Object-space normal of the unit-cube face nearest to p."""
    c = p - vec3(0.5)
    a = vec3(abs(c.x), abs(c.y), abs(c.z))
    if a.x >= a.y and a.x >= a.z:
        return vec3(1.0 if c.x > 0.0 else -1.0, 0.0, 0.0)
    if a.y >= a.z:
        return vec3(0.0, 1.0 if c.y > 0.0 else -1.0, 0.0)
    return vec3(0.0, 0.0, 1.0 if c.z > 0.0 else -1.0)


@func(exact=True)
def on_grid_edge(p: vec3, width: f32) -> bool:
    """True if p (on the unit-cube surface) lies within 'width' of a cube edge."""
    near_x = p.x < width or p.x > 1.0 - width
    near_y = p.y < width or p.y > 1.0 - width
    near_z = p.z < width or p.z > 1.0 - width
    return (near_x and near_y) or (near_y and near_z) or (near_x and near_z)


@func(exact=True)
def sphere_hit(o: vec3, d: vec3, c: vec3, r: f32, t_min: f32) -> f32:
    oc = o - c
    b = dot(oc, d)
    q = dot(oc, oc) - r * r
    disc = b * b - q
    if disc < 0.0:
        return INF
    s = sqrt(disc)
    t = -b - s
    if t > t_min:
        return t
    t = -b + s
    return select(t > t_min, t, INF)


@func(exact=True)
def capsule_hit(o: vec3, d: vec3, a: vec3, b: vec3, r: f32, t_min: f32) -> f32:
    """Ray vs capsule (segment a–b, radius r); assumes |d| = 1 (after Inigo Quilez)."""
    ba = b - a
    oa = o - a
    baba = dot(ba, ba)
    bard = dot(ba, d)
    baoa = dot(ba, oa)
    rdoa = dot(d, oa)
    oaoa = dot(oa, oa)
    qa = baba - bard * bard
    qb = baba * rdoa - baoa * bard
    qc = baba * oaoa - baoa * baoa - r * r * baba
    h = qb * qb - qa * qc
    if h < 0.0 or qa <= 0.0:
        return min(sphere_hit(o, d, a, r, t_min), sphere_hit(o, d, b, r, t_min))
    t = (-qb - sqrt(h)) / qa
    y = baoa + t * bard
    if y > 0.0 and y < baba and t > t_min:
        return t
    return min(sphere_hit(o, d, a, r, t_min), sphere_hit(o, d, b, r, t_min))


@func(exact=True)
def triangle_hit(o: vec3, d: vec3, p0: vec3, p1: vec3, p2: vec3, t_min: f32) -> f32:
    """Möller–Trumbore; returns INF on a miss."""
    e1 = p1 - p0
    e2 = p2 - p0
    pv = cross(d, e2)
    det = dot(e1, pv)
    if abs(det) < 1.0e-12:
        return INF
    inv = 1.0 / det
    tv = o - p0
    u = dot(tv, pv) * inv
    qv = cross(tv, e1)
    v = dot(d, qv) * inv
    t = dot(e2, qv) * inv
    ok = u >= 0.0 and v >= 0.0 and u + v <= 1.0 and t > t_min
    return select(ok, t, INF)
