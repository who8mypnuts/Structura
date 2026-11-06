from __future__ import annotations

from structura.kernels.skl import (
    INF,
    Buf,
    BufRW,
    dot,
    f32,
    func,
    kernel,
    max3,
    min3,
    normalize,
    select,
    struct,
    u32,
    uvec3,
    vec3,
)


@struct
class Hit:
    t: f32
    normal: vec3
    prim: u32


@func
def hash_u32(x: u32) -> u32:
    x ^= x >> 16
    x *= 0x7FEB352D
    x ^= x >> 15
    x *= 0x846CA68B
    x ^= x >> 16
    return x


@func(exact=True)
def box_normal(p: vec3) -> vec3:
    c = p - vec3(0.5)
    a = vec3(abs(c.x), abs(c.y), abs(c.z))
    if a.x >= a.y and a.x >= a.z:
        return vec3(select(c.x > 0.0, 1.0, -1.0), 0.0, 0.0)
    if a.y >= a.z:
        return vec3(0.0, select(c.y > 0.0, 1.0, -1.0), 0.0)
    return vec3(0.0, 0.0, select(c.z > 0.0, 1.0, -1.0))


@func(exact=True)
def intersect_unit_box(o: vec3, d: vec3, t_max: f32) -> Hit:
    inv = vec3(1.0) / d
    t0 = (vec3(0.0) - o) * inv
    t1 = (vec3(1.0) - o) * inv
    t_near = max3(min(t0, t1))
    t_far = min3(max(t0, t1))
    ok = t_near <= t_far and t_far > 0.0 and t_near < t_max
    t = select(t_near > 0.0, t_near, t_far)
    return Hit(select(ok, t, INF), box_normal(o + d * t), u32(0))


@kernel(workgroup=(8, 8, 1))
def render_boxes(gid: uvec3, width: u32, height: u32, boxes: Buf[f32], n_boxes: u32, result: BufRW[f32]) -> None:
    if gid.x >= width or gid.y >= height:
        return
    u = (f32(gid.x) + 0.5) / f32(width) * 2.0 - 1.0
    v = (f32(gid.y) + 0.5) / f32(height) * 2.0 - 1.0
    o = vec3(0.0, 0.0, -5.0)
    d = normalize(vec3(u, v, 2.0))
    best = INF
    shade = 0.0
    for i in range(n_boxes):
        base = i * 3
        org = vec3(boxes[base], boxes[base + 1], boxes[base + 2])
        h = intersect_unit_box(o - org, d, best)
        if h.t < best:
            best = h.t
            shade = dot(h.normal, normalize(vec3(1.0, 2.0, -3.0))) * 0.5 + 0.5
    noise = f32(hash_u32(gid.x + gid.y * width) & 255) / 255.0
    result[gid.x + gid.y * width] = select(best < INF, shade, noise * 0.1)
