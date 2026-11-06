"""Object-space intersections of the v2 solids (docs/05 §9.6): the ray is mapped into the instance's unit cube
with the stored inverse affine, so non-uniform scales and shears come for free. The ray parameter t is the
same in both spaces (affine maps keep it), and normals go back with the inverse transpose.

  ellipsoid: the sphere inscribed in the unit cube
  cylinder:  along x from (0,.5,.5) to (1,.5,.5); base radius 0.5, top radius 0.5 × prim_f[16] (a cone < 1)
  torus:     in the xy plane around the cube centre; tube radius prim_f[16], ring radius 0.5 − prim_f[16]
"""

from __future__ import annotations

from structura.kernels.skl import Buf, abs, dot, f32, func, length, max, sqrt, u32, vec3

from .hit import Hit, miss, normal_to_world, safe_inverse, to_object
from .shapes import unit_box_span

RK_ELLIPSOID, RK_CYLINDER, RK_TORUS = 5, 6, 7
TORUS_STEPS = 128
TORUS_EPS = 1.0e-5  # object units: below the renderer's surface offset, so a ray never re-hits its origin


@func(exact=True)
def hit_ellipsoid(prim_f: Buf[f32], base: u32, o: vec3, d: vec3, t_min: f32, t_max: f32) -> Hit:
    c = to_object(prim_f, base, o, 1.0) - vec3(0.5)
    dd = to_object(prim_f, base, d, 0.0)
    a = dot(dd, dd)
    b = dot(c, dd)
    disc = b * b - a * (dot(c, c) - 0.25)
    if disc < 0.0 or a <= 0.0:
        return miss()
    s = sqrt(disc)
    t = (-b - s) / a
    if t <= t_min:
        t = (-b + s) / a
    if t <= t_min or t > t_max:
        return miss()
    return Hit(t, normal_to_world(prim_f, base, c + dd * t), u32(0), u32(1))


@func(exact=True)
def cone_side(oo: vec3, dd: vec3, top: f32, t: f32, t_min: f32) -> bool:
    """t hits the side of the (truncated) cone between the caps."""
    x = oo.x + dd.x * t
    return t > t_min and x >= 0.0 and x <= 1.0 and 0.5 + 0.5 * (top - 1.0) * x >= 0.0


@func(exact=True)
def side_t(oo: vec3, dd: vec3, top: f32, t_min: f32) -> f32:
    """Nearest t > t_min on the side surface: (y−.5)² + (z−.5)² = R(x)², R(x) = 0.5 + 0.5(top − 1)x."""
    beta = 0.5 * (top - 1.0)
    oy = oo.y - 0.5
    oz = oo.z - 0.5
    r0 = 0.5 + beta * oo.x
    qa = dd.y * dd.y + dd.z * dd.z - beta * beta * dd.x * dd.x
    qb = oy * dd.y + oz * dd.z - beta * dd.x * r0
    qc = oy * oy + oz * oz - r0 * r0
    best = 3.0e38
    if abs(qa) < 1.0e-12:
        t = -qc / (2.0 * qb) if abs(qb) > 1.0e-20 else 3.0e38
        return t if cone_side(oo, dd, top, t, t_min) else best
    disc = qb * qb - qa * qc
    if disc < 0.0:
        return best
    s = sqrt(disc)
    t1 = (-qb - s) / qa
    t2 = (-qb + s) / qa
    if cone_side(oo, dd, top, t2, t_min):
        best = t2
    if cone_side(oo, dd, top, t1, t_min) and t1 < best:
        best = t1
    return best


@func(exact=True)
def cap_t(oo: vec3, dd: vec3, x: f32, radius: f32, t_min: f32) -> f32:
    inv = safe_inverse(dd)
    t = (x - oo.x) * inv.x
    p = oo + dd * t
    dy = p.y - 0.5
    dz = p.z - 0.5
    return t if t > t_min and dy * dy + dz * dz <= radius * radius else 3.0e38


@func(exact=True)
def hit_cylinder(prim_f: Buf[f32], base: u32, o: vec3, d: vec3, t_min: f32, t_max: f32) -> Hit:
    oo = to_object(prim_f, base, o, 1.0)
    dd = to_object(prim_f, base, d, 0.0)
    top = prim_f[base + 16]
    t = side_t(oo, dd, top, t_min)
    p = oo + dd * t
    n = vec3(-0.5 * (top - 1.0) * (0.5 + 0.5 * (top - 1.0) * p.x), p.y - 0.5, p.z - 0.5)
    t0 = cap_t(oo, dd, 0.0, 0.5, t_min)
    if t0 < t:
        t = t0
        n = vec3(-1.0, 0.0, 0.0)
    t1 = cap_t(oo, dd, 1.0, 0.5 * max(top, 0.0), t_min)
    if t1 < t:
        t = t1
        n = vec3(1.0, 0.0, 0.0)
    if t > t_max or t >= 3.0e38:
        return miss()
    return Hit(t, normal_to_world(prim_f, base, n), u32(0), u32(1))


@func(exact=True)
def torus_distance(p: vec3, minor: f32) -> f32:
    """Signed distance to the torus (object space)."""
    ring = length(vec3(p.x - 0.5, p.y - 0.5, 0.0)) - (0.5 - minor)
    return length(vec3(ring, p.z - 0.5, 0.0)) - minor


@func(exact=True)
def torus_normal(p: vec3, minor: f32) -> vec3:
    """Object-space normal: from the nearest point of the ring circle to p."""
    radial = vec3(p.x - 0.5, p.y - 0.5, 0.0)
    r = max(length(radial), 1.0e-12)
    centre = vec3(0.5, 0.5, 0.5) + radial * ((0.5 - minor) / r)
    return p - centre


@func(exact=True)
def hit_torus(prim_f: Buf[f32], base: u32, o: vec3, d: vec3, t_min: f32, t_max: f32) -> Hit:
    """Sphere tracing along the object-space ray, inside the unit cube that bounds the torus."""
    oo = to_object(prim_f, base, o, 1.0)
    dd = to_object(prim_f, base, d, 0.0)
    minor = prim_f[base + 16]
    span = unit_box_span(oo, safe_inverse(dd))
    speed = length(dd)
    if span.far < span.near or span.far < t_min or span.near > t_max or speed <= 0.0:
        return miss()
    t = max(span.near, t_min)
    end = span.far if span.far < t_max else t_max
    for _i in range(TORUS_STEPS):
        dist = abs(torus_distance(oo + dd * t, minor))
        if dist < TORUS_EPS and t > t_min:
            return Hit(t, normal_to_world(prim_f, base, torus_normal(oo + dd * t, minor)), u32(0), u32(1))
        t = t + max(dist, TORUS_EPS * 0.5) / speed
        if t > end:
            return miss()
    return miss()
