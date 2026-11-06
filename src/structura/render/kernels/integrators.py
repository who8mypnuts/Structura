"""First-hit integrators (docs/10 §2.2, §2.4): 'preview' (key light × AO) and 'ao' (Sunflow ambient occlusion)."""

from __future__ import annotations

from structura.kernels.skl import dot, f32, func, max, u32, vec3

from .buffers import SceneBufs
from .camera import cfg3
from .layout import AO_DIST, EPS, SUN_DIR
from .lights import offset
from .sampling import cosine_hemisphere, rand01
from .scene import NO_HIT, TRACE_ANY, Hit, trace
from .surface import surface_at


@func
def ambient_occlusion(
    p: vec3, n: vec3, samples: u32, max_dist: f32, pixel: u32, sample_index: u32, dim: u32, sc: SceneBufs
) -> f32:
    """Fraction of cosine-weighted rays that escape within max_dist (1 = fully open)."""
    open_rays = 0.0
    o = offset(p, n, sc.cfg[EPS])
    for i in range(samples):
        d = cosine_hemisphere(n, rand01(pixel, sample_index, dim + 2 * i), rand01(pixel, sample_index, dim + 2 * i + 1))
        h = trace(o, d, 0.0, max_dist, u32(TRACE_ANY), u32(NO_HIT), sc)
        if h.prim == NO_HIT:
            open_rays += 1.0
    return open_rays / f32(max(samples, u32(1)))


@func
def shade_first_hit(
    h: Hit, o: vec3, d: vec3, mode: u32, ao_samples: u32, pixel: u32, sample_index: u32, sc: SceneBufs
) -> vec3:
    """'preview' (mode 0) and 'ao' (mode 1) shading of a primary hit."""
    p = o + d * h.t
    s = surface_at(sc, h.prim)
    occ = ambient_occlusion(p, h.normal, ao_samples, sc.cfg[AO_DIST], pixel, sample_index, u32(10), sc)
    if mode == 1:
        return s.base * occ + s.emission
    key = max(dot(h.normal, cfg3(sc.cfg, SUN_DIR)), 0.0)
    return s.base * ((0.35 + 0.65 * key) * (0.4 + 0.6 * occ)) + s.emission
