"""Render pass kernel: adds 'spp' samples to every active pixel of a band of rows (or a tile) in the film
'accum' (layout.FILM_F floats per pixel: RGB + weight sums, then the same for the even-numbered samples)."""

from __future__ import annotations

from structura.kernels.skl import Buf, BufRW, clamp, f32, floor, func, kernel, min, struct, u32, uvec3, vec3

from .buffers import SceneBufs
from .camera import camera_ray
from .classic import classic_radiance
from .color import srgb_decode
from .integrators import shade_first_hit
from .layout import (
    CLAMP,
    FILM_F,
    FILTER_BASE,
    FILTER_ON,
    FILTER_RADIUS,
    FILTER_SIGNS,
    FILTER_TABLE,
    INTEGRATOR_CLASSIC,
    INTEGRATOR_PATH,
)
from .opacity import visible_hit
from .path import escaped, path_radiance
from .sampling import sample01
from .scene import NO_HIT


@struct
class FilterSample:
    offset: f32  # from the pixel centre, in pixels
    sign: f32


@func
def filter_sample(cfg: Buf[f32], u: f32, radius: f32) -> FilterSample:
    """Invert the filter's tabulated |f| CDF; the sign of f at the offset weights the sample."""
    at = u * f32(FILTER_TABLE)
    k = u32(min(floor(at), f32(FILTER_TABLE - 1)))
    base = u32(FILTER_BASE)
    x = cfg[base + k] + (cfg[base + k + 1] - cfg[base + k]) * (at - f32(k))
    bin = u32(clamp((x + radius) / (2.0 * radius) * f32(FILTER_SIGNS), 0.0, f32(FILTER_SIGNS - 1)))
    return FilterSample(x, cfg[base + u32(FILTER_TABLE + 1) + bin])


@struct
class PixelSample:
    x: f32  # offset inside the pixel grid, in pixels (0..1 for the box filter)
    y: f32
    weight: f32  # the filter's sign (±1)


@func
def pixel_sample(sc: SceneBufs, pixel: u32, s: u32) -> PixelSample:
    ox = sample01(sc.cfg, pixel, s, u32(0))
    oy = sample01(sc.cfg, pixel, s, u32(1))
    if sc.cfg[FILTER_ON] == 0.0:
        return PixelSample(ox, oy, 1.0)
    fx = filter_sample(sc.cfg, ox, sc.cfg[FILTER_RADIUS])
    fy = filter_sample(sc.cfg, oy, sc.cfg[FILTER_RADIUS])
    return PixelSample(fx.offset + 0.5, fy.offset + 0.5, fx.sign * fy.sign)


@func
def sample_radiance(
    ray_o: vec3, ray_d: vec3, integrator: u32, max_bounces: u32, ao_samples: u32, pixel: u32, s: u32, sc: SceneBufs
) -> vec3:
    """Returns one radiance sample of a camera ray with the chosen integrator.

    Rays that miss see the background colour, or the sky when the script declares an environment.

    Args:
        ray_o: The ray origin.
        ray_d: The ray direction.
        integrator: INTEGRATOR_* of kernels/layout.py.
        max_bounces: The path tracer's longest path.
        ao_samples: Occlusion rays for the preview and ao integrators.
        pixel: The pixel (random-number stream).
        s: The sample (random-number stream).
        sc: The scene buffers.
    """
    if integrator == INTEGRATOR_PATH:
        return path_radiance(ray_o, ray_d, max_bounces, pixel, s, sc)
    if integrator == INTEGRATOR_CLASSIC:
        return srgb_decode(classic_radiance(ray_o, ray_d, max_bounces, ao_samples, pixel, s, sc))
    h = visible_hit(ray_o, ray_d, pixel, s, sc)
    if h.prim == NO_HIT:  # the background colour, or the sky when the script declares an environment
        return escaped(sc, ray_d, True, 0.0, False)
    return shade_first_hit(h, ray_o, ray_d, integrator, ao_samples, pixel, s, sc)


@func
def add_to_film(accum: BufRW[f32], pixel: u32, total: vec3, weights: f32, even: vec3, even_weights: f32) -> None:
    at = pixel * u32(FILM_F)
    accum[at] = accum[at] + total.x
    accum[at + 1] = accum[at + 1] + total.y
    accum[at + 2] = accum[at + 2] + total.z
    accum[at + 3] = accum[at + 3] + weights
    accum[at + 4] = accum[at + 4] + even.x
    accum[at + 5] = accum[at + 5] + even.y
    accum[at + 6] = accum[at + 6] + even.z
    accum[at + 7] = accum[at + 7] + even_weights


@kernel(workgroup=(8, 8, 1))
def render_pass(
    gid: uvec3,
    width: u32,
    height: u32,
    row0: u32,
    col0: u32,
    sample_base: u32,
    spp: u32,
    integrator: u32,
    max_bounces: u32,
    ao_samples: u32,
    sc: SceneBufs,
    pixel_mask: Buf[u32],
    accum: BufRW[f32],
) -> None:
    x = gid.x + col0  # the dispatch covers a band of rows (or a tile) starting at (col0, row0)
    y = gid.y + row0
    if x >= width or y >= height:
        return
    pixel = x + y * width
    if pixel_mask[pixel] == u32(0):  # converged (adaptive sampling) or outside the render region
        return
    total = vec3(0.0)
    even = vec3(0.0)
    weights = 0.0
    even_weights = 0.0
    limit = sc.cfg[CLAMP]
    for k in range(spp):
        s = sample_base + k
        ps = pixel_sample(sc, pixel, s)
        sx = ((f32(x) + ps.x) / f32(width)) * 2.0 - 1.0
        sy = 1.0 - ((f32(y) + ps.y) / f32(height)) * 2.0
        ray = camera_ray(sc.cfg, sx, sy, sample01(sc.cfg, pixel, s, u32(2)), sample01(sc.cfg, pixel, s, u32(3)))
        color = sample_radiance(ray.o, ray.d, integrator, max_bounces, ao_samples, pixel, s, sc)
        weighted = vec3(min(color.x, limit), min(color.y, limit), min(color.z, limit)) * ps.weight
        total = total + weighted
        weights = weights + ps.weight
        if (s & u32(1)) == u32(0):
            even = even + weighted
            even_weights = even_weights + ps.weight
    add_to_film(accum, pixel, total, weights, even, even_weights)
