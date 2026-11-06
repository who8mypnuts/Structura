"""The hit record and object-space helpers shared by the intersection routines (layouts: render/pack.py)."""

from __future__ import annotations

from structura.kernels.skl import INF, Buf, abs, f32, func, normalize, struct, u32, vec3

NO_HIT = 0xFFFFFFFF


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
