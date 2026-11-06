"""Environment lookup and importance sampling (docs/10 §4; host side: render/environment.py).

With a map (ENV_ON), radiance comes from the equirectangular 'env_f' texels; otherwise from the analytic
colour/gradient sky. Sampling inverts the marginal/conditional CDFs stored after the texels in the same
buffer (at w·h·3); the pdf of a direction is derived from the same CDF differences, so no extra table is needed.
"""

from __future__ import annotations

from structura.kernels.skl import PI, Buf, acos, atan2, clamp, cos, f32, floor, fract, func, max, sin, struct, u32, vec3

from .buffers import SceneBufs
from .layout import ENV_H, ENV_ON, ENV_ROT, ENV_SCALE, ENV_W
from .lights import sky


@struct
class EnvSample:
    d: vec3
    pdf: f32  # solid-angle density
    radiance: vec3


@func
def env_uv_u(sc: SceneBufs, d: vec3) -> f32:
    return fract(atan2(d.x, d.z * -1.0) / (2.0 * PI) + 0.5 - sc.cfg[ENV_ROT] / (2.0 * PI) + 1.0)


@func
def env_texel(sc: SceneBufs, d: vec3) -> u32:
    w = u32(sc.cfg[ENV_W])
    h = u32(sc.cfg[ENV_H])
    col = min_u32(u32(floor(env_uv_u(sc, d) * f32(w))), w - 1)
    row = min_u32(u32(floor(acos(clamp(d.y, -1.0, 1.0)) / PI * f32(h))), h - 1)
    return row * w + col


@func
def min_u32(a: u32, b: u32) -> u32:
    return a if a < b else b


@func
def texel_rgb(env_f: Buf[f32], texel: u32) -> vec3:
    return vec3(env_f[texel * 3], env_f[texel * 3 + 1], env_f[texel * 3 + 2])


@func
def env_radiance(sc: SceneBufs, d: vec3) -> vec3:
    if sc.cfg[ENV_ON] == 0.0:
        return sky(sc.cfg, d)
    return texel_rgb(sc.env_f, env_texel(sc, d)) * sc.cfg[ENV_SCALE]


@func
def env_pdf(sc: SceneBufs, d: vec3) -> f32:
    """Solid-angle pdf of env_sample for direction d (0 without a map)."""
    if sc.cfg[ENV_ON] == 0.0:
        return 0.0
    w = u32(sc.cfg[ENV_W])
    h = u32(sc.cfg[ENV_H])
    texel = env_texel(sc, d)
    row = texel // w
    col = texel - row * w
    cdf = w * h * 3
    row_prob = sc.env_f[cdf + row + 1] - sc.env_f[cdf + row]
    base = cdf + h + 1 + row * (w + 1)
    col_prob = sc.env_f[base + col + 1] - sc.env_f[base + col]
    sin_theta = max(sin((f32(row) + 0.5) / f32(h) * PI), 1.0e-4)
    return row_prob * col_prob * f32(w) * f32(h) / (2.0 * PI * PI * sin_theta)


@func
def cdf_search(env_f: Buf[f32], base: u32, n: u32, u: f32) -> u32:
    """The interval k in [0, n) with env_f[base + k] <= u < env_f[base + k + 1] (binary search).

    (Buffer parameters keep the buffer's own name: WGSL and GLSL bind buffers as globals.)"""
    lo = u32(0)
    hi = n
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if env_f[base + mid] <= u:
            lo = mid
        else:
            hi = mid
    return lo


@func
def env_sample(sc: SceneBufs, u1: f32, u2: f32) -> EnvSample:
    w = u32(sc.cfg[ENV_W])
    h = u32(sc.cfg[ENV_H])
    cdf = w * h * 3
    row = cdf_search(sc.env_f, cdf, h, u1)
    base = cdf + h + 1 + row * (w + 1)
    col = cdf_search(sc.env_f, base, w, u2)
    lo_u = sc.env_f[base + col]
    frac = clamp((u2 - lo_u) / max(sc.env_f[base + col + 1] - lo_u, 1.0e-12), 0.0, 1.0)
    theta = (f32(row) + 0.5) / f32(h) * PI
    phi = ((f32(col) + frac) / f32(w) - 0.5) * 2.0 * PI + sc.cfg[ENV_ROT]
    d = vec3(sin(theta) * sin(phi), cos(theta), sin(theta) * cos(phi) * -1.0)
    return EnvSample(d, env_pdf(sc, d), env_radiance(sc, d))
