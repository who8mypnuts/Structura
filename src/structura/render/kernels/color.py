"""sRGB transfer functions on the device (the host versions live in core/color/srgb.py)."""

from __future__ import annotations

from structura.kernels.skl import f32, func, max, pow, vec3


@func
def encode1(c: f32) -> f32:
    x = max(c, 0.0)
    return x * 12.92 if x <= 0.0031308 else 1.055 * pow(x, 1.0 / 2.4) - 0.055


@func
def decode1(c: f32) -> f32:
    x = max(c, 0.0)
    return x / 12.92 if x <= 0.04045 else pow((x + 0.055) / 1.055, 2.4)


@func
def srgb_encode(c: vec3) -> vec3:
    return vec3(encode1(c.x), encode1(c.y), encode1(c.z))


@func
def srgb_decode(c: vec3) -> vec3:
    return vec3(decode1(c.x), decode1(c.y), decode1(c.z))
