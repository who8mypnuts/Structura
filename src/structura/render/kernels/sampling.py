"""Random numbers and warps (integer-exact on every target, docs/11 §8)."""

from __future__ import annotations

from structura.kernels.skl import PI, Buf, cos, dot, f32, floor, func, max, min, sin, sqrt, u32, vec3

from .layout import SEQUENCE

INV_2_24 = 1.0 / 16777216.0
HALTON_DIMS = 16  # dimensions with a Halton base: pixel (0-1), lens (2-3), the first bounce (32-43)
ONE_MINUS = 0.99999994


@func
def hash_u32(x: u32) -> u32:
    """A 32-bit integer hash (low bias, cheap)."""
    x ^= x >> 16
    x *= 0x7FEB352D
    x ^= x >> 15
    x *= 0x846CA68B
    x ^= x >> 16
    return x


@func
def rand01(pixel: u32, sample_index: u32, dim: u32) -> f32:
    """Uniform in [0, 1) for (pixel, sample, dimension): decorrelated by nested hashing."""
    h = hash_u32(pixel ^ hash_u32(sample_index * 0x9E3779B9 + hash_u32(dim + 0x632BE5AB)))
    return f32(h >> 8) * INV_2_24


@func
def halton_prime(k: u32) -> u32:
    """The prime base of Halton slot k (0 ≤ k < HALTON_DIMS)."""
    if k < 4:
        return u32(2) if k == 0 else (u32(3) if k == 1 else (u32(5) if k == 2 else u32(7)))
    if k < 8:
        return u32(11) if k == 4 else (u32(13) if k == 5 else (u32(17) if k == 6 else u32(19)))
    if k < 12:
        return u32(23) if k == 8 else (u32(29) if k == 9 else (u32(31) if k == 10 else u32(37)))
    return u32(41) if k == 12 else (u32(43) if k == 13 else (u32(47) if k == 14 else u32(53)))


@func
def radical_inverse(i: u32, base: u32) -> f32:
    """The digits of i in ``base`` mirrored behind the point (the Halton sequence's coordinate)."""
    inv = 1.0 / f32(base)
    f = inv
    r = 0.0
    n = i
    while n > u32(0):
        r = r + f32(n % base) * f
        n = n // base
        f = f * inv
    return r


@func
def halton_slot(dim: u32) -> u32:
    """The Halton slot of a sample dimension; HALTON_DIMS for dimensions that stay hashed random."""
    if dim < 4:
        return dim
    if dim >= 32 and dim < 44:
        return dim - 28
    return u32(HALTON_DIMS)


@func
def sample01(cfg: Buf[f32], pixel: u32, sample_index: u32, dim: u32) -> f32:
    """rand01, or (cfg SEQUENCE = 1) the Halton sequence, Cranley–Patterson rotated per pixel (docs/09 §4)."""
    k = halton_slot(dim)
    if cfg[SEQUENCE] == 0.0 or k >= u32(HALTON_DIMS):
        return rand01(pixel, sample_index, dim)
    v = radical_inverse(sample_index, halton_prime(k)) + rand01(pixel, u32(0x5EED5EED), dim)
    return min(v - floor(v), ONE_MINUS)


@func
def orthonormal_u(n: vec3) -> vec3:
    """A unit vector perpendicular to n (Duff et al. 2017 branchless basis)."""
    s = 1.0 if n.z >= 0.0 else -1.0
    a = -1.0 / (s + n.z)
    b = n.x * n.y * a
    return vec3(1.0 + s * n.x * n.x * a, s * b, -s * n.x)


@func
def orthonormal_v(n: vec3) -> vec3:
    s = 1.0 if n.z >= 0.0 else -1.0
    a = -1.0 / (s + n.z)
    b = n.x * n.y * a
    return vec3(b, s + n.y * n.y * a, -n.y)


@func
def cosine_local(u1: f32, u2: f32) -> vec3:
    """Cosine-weighted direction around +z."""
    r = sqrt(u1)
    phi = 2.0 * PI * u2
    return vec3(r * cos(phi), r * sin(phi), sqrt(max(0.0, 1.0 - u1)))


@func
def to_local(v: vec3, n: vec3) -> vec3:
    """World → shading frame (orthonormal_u, orthonormal_v, n)."""
    return vec3(dot(v, orthonormal_u(n)), dot(v, orthonormal_v(n)), dot(v, n))


@func
def to_world(v: vec3, n: vec3) -> vec3:
    return orthonormal_u(n) * v.x + orthonormal_v(n) * v.y + n * v.z


@func
def cosine_hemisphere(n: vec3, u1: f32, u2: f32) -> vec3:
    """Cosine-weighted direction around the unit normal n."""
    return to_world(cosine_local(u1, u2), n)


@func
def uniform_sphere(u1: f32, u2: f32) -> vec3:
    z = 1.0 - 2.0 * u1
    r = sqrt(max(0.0, 1.0 - z * z))
    phi = 2.0 * PI * u2
    return vec3(r * cos(phi), r * sin(phi), z)


@func
def cone_direction(axis: vec3, cos_max: f32, u1: f32, u2: f32) -> vec3:
    """Uniform direction inside the cone around 'axis' with half-angle acos(cos_max)."""
    cos_t = 1.0 - u1 * (1.0 - cos_max)
    sin_t = sqrt(max(0.0, 1.0 - cos_t * cos_t))
    phi = 2.0 * PI * u2
    return orthonormal_u(axis) * (sin_t * cos(phi)) + orthonormal_v(axis) * (sin_t * sin(phi)) + axis * cos_t
