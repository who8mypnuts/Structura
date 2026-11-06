"""Render pass kernel: adds 'spp' samples per pixel to the float accumulation buffer (RGB sum + count)."""

from __future__ import annotations

from structura.kernels.skl import BufRW, f32, kernel, min, u32, uvec3, vec3

from .buffers import SceneBufs
from .camera import camera_ray, cfg3
from .classic import classic_radiance
from .color import srgb_decode
from .integrators import shade_first_hit
from .layout import BACKGROUND, CLAMP, INTEGRATOR_CLASSIC, INTEGRATOR_PATH
from .path import path_radiance
from .sampling import rand01
from .scene import NO_HIT, trace


@kernel(workgroup=(8, 8, 1))
def render_pass(
    gid: uvec3,
    width: u32,
    height: u32,
    sample_base: u32,
    spp: u32,
    integrator: u32,
    max_bounces: u32,
    ao_samples: u32,
    sc: SceneBufs,
    accum: BufRW[f32],
) -> None:
    if gid.x >= width or gid.y >= height:
        return
    pixel = gid.x + gid.y * width
    total = vec3(0.0)
    for k in range(spp):
        s = sample_base + k
        sx = ((f32(gid.x) + rand01(pixel, s, u32(0))) / f32(width)) * 2.0 - 1.0
        sy = 1.0 - ((f32(gid.y) + rand01(pixel, s, u32(1))) / f32(height)) * 2.0
        ray = camera_ray(sc.cfg, sx, sy, rand01(pixel, s, u32(2)), rand01(pixel, s, u32(3)))
        color = vec3(0.0)
        if integrator == INTEGRATOR_PATH:
            color = path_radiance(ray.o, ray.d, max_bounces, pixel, s, sc)
        elif integrator == INTEGRATOR_CLASSIC:
            color = srgb_decode(classic_radiance(ray.o, ray.d, max_bounces, ao_samples, pixel, s, sc))
        else:
            h = trace(ray.o, ray.d, 0.0, 3.0e38, u32(0), u32(NO_HIT), sc)
            color = cfg3(sc.cfg, BACKGROUND)
            if h.prim != NO_HIT:
                color = shade_first_hit(h, ray.o, ray.d, integrator, ao_samples, pixel, s, sc)
        limit = sc.cfg[CLAMP]
        total = total + vec3(min(color.x, limit), min(color.y, limit), min(color.z, limit))
    at = pixel * 4
    accum[at] = accum[at] + total.x
    accum[at + 1] = accum[at + 1] + total.y
    accum[at + 2] = accum[at + 2] + total.z
    accum[at + 3] = accum[at + 3] + f32(spp)
