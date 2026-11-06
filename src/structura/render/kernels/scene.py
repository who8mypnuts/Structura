"""Scene access and BVH traversal (layouts: render/pack.py and render/bvh.py).

Buffer parameters keep the same names everywhere (WGSL/GLSL bind them as globals).
"""

from __future__ import annotations

from structura.kernels.skl import (
    INF,
    Buf,
    abs,
    clamp,
    cross,
    dot,
    f32,
    func,
    local,
    max3,
    min3,
    normalize,
    struct,
    u32,
    vec3,
)

from .buffers import SceneBufs
from .shapes import box_face_normal, capsule_hit, on_grid_edge, sphere_hit, triangle_hit, unit_box_span

PRIM_F = 24
PRIM_U = 4
NO_HIT = 0xFFFFFFFF
TRACE_ANY = 1  # trace() flags: stop at the first hit (shadow / occlusion rays)
TRACE_OPAQUE = 2  # ignore primitives whose instance alpha is < 1 (Structure Synth shadow rule)
RK_BOX = 0
RK_SPHERE = 1
RK_CAPSULE = 2
RK_TRIANGLE = 3
RK_GRID = 4


@struct
class Hit:
    t: f32
    normal: vec3  # unit, facing the incoming ray
    prim: u32
    front: u32  # 1: the ray arrived from the outside (geometric normal opposed the ray)


@func
def miss() -> Hit:
    return Hit(INF, vec3(0.0), u32(NO_HIT), u32(0))


@func(exact=True)
def safe_inverse(d: vec3) -> vec3:
    """1/d with zero components replaced by a huge finite value (WGSL leaves 1/0 indeterminate)."""
    x = d.x if abs(d.x) > 1.0e-20 else 1.0e-20
    y = d.y if abs(d.y) > 1.0e-20 else 1.0e-20
    z = d.z if abs(d.z) > 1.0e-20 else 1.0e-20
    return vec3(1.0 / x, 1.0 / y, 1.0 / z)


@func(exact=True)
def to_object(prim_f: Buf[f32], base: u32, p: vec3, w: f32) -> vec3:
    """Apply the stored inverse affine to a point (w = 1) or a direction (w = 0)."""
    x = prim_f[base] * p.x + prim_f[base + 1] * p.y + prim_f[base + 2] * p.z + prim_f[base + 3] * w
    y = prim_f[base + 4] * p.x + prim_f[base + 5] * p.y + prim_f[base + 6] * p.z + prim_f[base + 7] * w
    z = prim_f[base + 8] * p.x + prim_f[base + 9] * p.y + prim_f[base + 10] * p.z + prim_f[base + 11] * w
    return vec3(x, y, z)


@func(exact=True)
def normal_to_world(prim_f: Buf[f32], base: u32, n: vec3) -> vec3:
    """(M⁻¹)ᵀ · n — normals transform with the inverse transpose."""
    x = prim_f[base] * n.x + prim_f[base + 4] * n.y + prim_f[base + 8] * n.z
    y = prim_f[base + 1] * n.x + prim_f[base + 5] * n.y + prim_f[base + 9] * n.z
    z = prim_f[base + 2] * n.x + prim_f[base + 6] * n.y + prim_f[base + 10] * n.z
    return normalize(vec3(x, y, z))


@func(exact=True)
def hit_box(prim_f: Buf[f32], base: u32, o: vec3, d: vec3, t_min: f32, t_max: f32, wire: bool) -> Hit:
    oo = to_object(prim_f, base, o, 1.0)
    dd = to_object(prim_f, base, d, 0.0)
    span = unit_box_span(oo, safe_inverse(dd))
    t = span.near
    if span.far < span.near or span.far < t_min or span.near > t_max:
        return miss()
    if t <= t_min or (wire and not on_grid_edge(oo + dd * t, prim_f[base + 16])):
        t = span.far
        if wire and not on_grid_edge(oo + dd * t, prim_f[base + 16]):
            return miss()
    if t > t_max:
        return miss()
    return Hit(t, normal_to_world(prim_f, base, box_face_normal(oo + dd * t)), u32(0), u32(1))


@func(exact=True)
def hit_prim(
    prim: u32, o: vec3, d: vec3, t_min: f32, t_max: f32, prim_f: Buf[f32], prim_u: Buf[u32], tri_f: Buf[f32]
) -> Hit:
    base = prim * PRIM_F
    kind = prim_u[prim * PRIM_U]
    h = miss()
    if kind == RK_BOX or kind == RK_GRID:
        h = hit_box(prim_f, base, o, d, t_min, t_max, kind == RK_GRID)
    elif kind == RK_SPHERE:
        c = vec3(prim_f[base + 16], prim_f[base + 17], prim_f[base + 18])
        t = sphere_hit(o, d, c, prim_f[base + 19], t_min)
        h = Hit(t, normalize(o + d * t - c), prim, u32(1))
    elif kind == RK_CAPSULE:
        a = vec3(prim_f[base + 16], prim_f[base + 17], prim_f[base + 18])
        b = vec3(prim_f[base + 19], prim_f[base + 20], prim_f[base + 21])
        t = capsule_hit(o, d, a, b, prim_f[base + 22], t_min)
        p = o + d * t
        s = clamp(dot(p - a, b - a) / max(dot(b - a, b - a), 1.0e-20), 0.0, 1.0)
        h = Hit(t, normalize(p - (a + (b - a) * s)), prim, u32(1))
    else:
        tb = prim_u[prim * PRIM_U + 3] * 9
        p0 = vec3(tri_f[tb], tri_f[tb + 1], tri_f[tb + 2])
        p1 = vec3(tri_f[tb + 3], tri_f[tb + 4], tri_f[tb + 5])
        p2 = vec3(tri_f[tb + 6], tri_f[tb + 7], tri_f[tb + 8])
        h = Hit(triangle_hit(o, d, p0, p1, p2, t_min), normalize(cross(p1 - p0, p2 - p0)), prim, u32(1))
    if h.t > t_max:
        return miss()
    outside = dot(h.normal, d) <= 0.0
    return Hit(h.t, h.normal if outside else h.normal * -1.0, prim, u32(1) if outside else u32(0))


@func(exact=True)
def node_entry(node_f: Buf[f32], node: u32, o: vec3, inv: vec3) -> f32:
    b = node * 6
    t0 = (vec3(node_f[b], node_f[b + 1], node_f[b + 2]) - o) * inv
    t1 = (vec3(node_f[b + 3], node_f[b + 4], node_f[b + 5]) - o) * inv
    near = max(max3(min(t0, t1)), 0.0)
    far = min3(max(t0, t1))
    return near if near <= far else INF


@func
def skipped(prim: u32, flags: u32, exclude: u32, prim_f: Buf[f32], prim_u: Buf[u32]) -> bool:
    """Primitives a ray ignores: the excluded instance, and see-through ones for TRACE_OPAQUE rays."""
    if exclude != u32(NO_HIT) and prim_u[prim * PRIM_U + 2] == exclude:
        return True
    return (flags & u32(TRACE_OPAQUE)) != u32(0) and prim_f[prim * PRIM_F + 15] < 1.0


@func(exact=True)
def hit_leaf(
    first: u32,
    count: u32,
    o: vec3,
    d: vec3,
    t_min: f32,
    best: Hit,
    flags: u32,
    exclude: u32,
    sc: SceneBufs,
) -> Hit:
    """Test the primitives of one BVH leaf against the current best hit."""
    result = best
    for k in range(first, first + count):
        prim = sc.order[k]
        if skipped(prim, flags, exclude, sc.prim_f, sc.prim_u):
            continue
        h = hit_prim(prim, o, d, t_min, result.t, sc.prim_f, sc.prim_u, sc.tri_f)
        if h.t < result.t:
            result = h
            if (flags & u32(TRACE_ANY)) != u32(0):
                return result
    return result


@func(exact=True)
def trace(
    o: vec3,
    d: vec3,
    t_min: f32,
    t_max: f32,
    flags: u32,
    exclude: u32,
    sc: SceneBufs,
) -> Hit:
    """Closest hit along o + t·d for t in (t_min, t_max); TRACE_* flags; 'exclude' = instance row or NO_HIT."""
    inv = safe_inverse(d)
    stack = local(u32, 64)
    stack[0] = u32(0)
    sp = u32(1)
    best = Hit(t_max, vec3(0.0), u32(NO_HIT), u32(0))
    while sp > 0:
        sp -= 1
        node = stack[sp]
        if node_entry(sc.node_f, node, o, inv) >= best.t:
            continue
        count = sc.node_u[node * 2 + 1]
        first = sc.node_u[node * 2]
        if count > 0:
            best = hit_leaf(first, count, o, d, t_min, best, flags, exclude, sc)
            if (flags & u32(TRACE_ANY)) != u32(0) and best.prim != u32(NO_HIT):
                return best
        elif sp + 2 <= 64:
            near_first = node_entry(sc.node_f, first, o, inv) <= node_entry(sc.node_f, first + 1, o, inv)
            stack[sp] = first + 1 if near_first else first
            stack[sp + 1] = first if near_first else first + 1
            sp += 2
    return best
