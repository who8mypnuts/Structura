"""First-hit integrators (docs/10 §2.2, §2.4): 'preview' (key light × AO) and 'ao' (Sunflow ambient occlusion)."""

from __future__ import annotations

from structura.kernels.skl import INF, PI, dot, func, max, max3, u32, vec3

from .buffers import SceneBufs
from .camera import cfg3
from .layout import AO_DIRECT, AO_DIST, N_LIGHTS, SUN_COS, SUN_DIR, SUN_IRRADIANCE
from .lights import light_sample, unoccluded
from .models import ambient_occlusion, is_special, special_radiance
from .sampling import cone_direction, rand01
from .scene import Hit
from .surface import surface_at


@func
def direct_lambert(sc: SceneBufs, p: vec3, n: vec3, pixel: u32, sample_index: u32) -> vec3:
    """'ao.direct': irradiance from the sun and the declared lights over π (a white Lambertian surface)."""
    ldir = cone_direction(cfg3(sc.cfg, SUN_DIR), sc.cfg[SUN_COS], rand01(pixel, sample_index, u32(6)),
                          rand01(pixel, sample_index, u32(7)))  # fmt: skip
    e = cfg3(sc.cfg, SUN_IRRADIANCE) * max(dot(ldir, n), 0.0)
    total = e if max3(e) > 0.0 and unoccluded(sc, p, n, ldir, INF) else vec3(0.0)
    for i in range(u32(sc.cfg[N_LIGHTS])):
        ls = light_sample(sc, u32(i), p, rand01(pixel, sample_index, u32(8)), rand01(pixel, sample_index, u32(9)))
        cos_l = max(dot(ls.d, n), 0.0)
        if cos_l > 0.0 and unoccluded(sc, p, n, ls.d, ls.dist * 0.999):
            total = total + ls.irradiance * cos_l
    return total * (1.0 / PI)


@func
def shade_first_hit(
    h: Hit, o: vec3, d: vec3, mode: u32, ao_samples: u32, pixel: u32, sample_index: u32, sc: SceneBufs
) -> vec3:
    """'preview' (mode 0) and 'ao' (mode 1) shading of a primary hit."""
    p = o + d * h.t
    s = surface_at(sc, h.prim)
    if is_special(sc.mat_f, s.mat):
        return special_radiance(sc, h, p, d, s, pixel, sample_index, u32(40))
    occ = ambient_occlusion(p, h.normal, ao_samples, sc.cfg[AO_DIST], pixel, sample_index, u32(10), sc)
    if mode == 1:
        lit = direct_lambert(sc, p, h.normal, pixel, sample_index) if sc.cfg[AO_DIRECT] != 0.0 else vec3(0.0)
        return s.base * (occ + lit) + s.emission
    key = max(dot(h.normal, cfg3(sc.cfg, SUN_DIR)), 0.0)
    return s.base * ((0.35 + 0.65 * key) * (0.4 + 0.6 * occ)) + s.emission
