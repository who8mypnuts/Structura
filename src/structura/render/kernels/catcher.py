"""Shadow catcher (docs/10 §2.3 'Ground'): the fraction of the incoming light that the scene lets through to a
point, estimated with one sample each of the sun, the sky and every declared light. A camera ray that hits
a shadow-catcher surface shows the background multiplied by this ratio."""

from __future__ import annotations

from structura.kernels.skl import INF, PI, dot, f32, func, max, u32, vec3

from .buffers import SceneBufs
from .camera import cfg3
from .environment import env_radiance
from .layout import N_LIGHTS, SUN_COS, SUN_DIR, SUN_IRRADIANCE
from .lights import light_sample, unoccluded
from .microfacet import luminance
from .sampling import cone_direction, cosine_hemisphere, rand01


@func
def shadow_ratio(sc: SceneBufs, p: vec3, n: vec3, pixel: u32, sample_index: u32, dim: u32) -> f32:
    """Light that arrives at p ÷ light that would arrive without the scene (1 where nothing lights p)."""
    u1 = rand01(pixel, sample_index, dim)
    u2 = rand01(pixel, sample_index, dim + 1)
    ldir = cone_direction(cfg3(sc.cfg, SUN_DIR), sc.cfg[SUN_COS], u1, u2)
    sun = luminance(cfg3(sc.cfg, SUN_IRRADIANCE)) * max(dot(ldir, n), 0.0)
    full = sun
    lit = sun if sun > 0.0 and unoccluded(sc, p, n, ldir, INF) else 0.0
    d = cosine_hemisphere(n, rand01(pixel, sample_index, dim + 2), rand01(pixel, sample_index, dim + 3))
    sky = luminance(env_radiance(sc, d)) * PI  # ∫ L cos dω with one cosine-weighted sample
    full = full + sky
    if sky > 0.0 and unoccluded(sc, p, n, d, INF):
        lit = lit + sky
    for i in range(u32(sc.cfg[N_LIGHTS])):
        ls = light_sample(sc, u32(i), p, u1, u2)
        e = luminance(ls.irradiance) * max(dot(ls.d, n), 0.0)
        full = full + e
        if e > 0.0 and unoccluded(sc, p, n, ls.d, ls.dist * 0.999):
            lit = lit + e
    return lit / full if full > 0.0 else 1.0
