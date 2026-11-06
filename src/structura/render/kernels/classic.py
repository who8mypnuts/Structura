"""'classic': Structure Synth 1.5's internal raytracer (docs/10 §2.1, RenderThread::rayCast).

Shading happens in display (sRGB) space like the original; the pass kernel decodes the result to linear.
The original recursion (transparency and reflection) becomes a stochastic walk with the same expected
value: at each hit one continuation is chosen with probability proportional to its weight.
"""

from __future__ import annotations

from structura.kernels.skl import INF, dot, f32, func, length, max, normalize, pow, u32, vec3

from .buffers import SceneBufs
from .camera import cfg3
from .color import srgb_encode
from .layout import (
    BACKGROUND,
    LIGHT_POS,
    M_LEGACY_AMBIENT,
    M_LEGACY_DIFFUSE,
    M_LEGACY_REFLECTION,
    M_LEGACY_SPECULAR,
    MAT_F,
    SHADOWS,
)
from .sampling import rand01, uniform_sphere
from .scene import NO_HIT, PRIM_F, PRIM_U, TRACE_ANY, TRACE_OPAQUE, Hit, trace
from .surface import surface_at


@func
def classic_ao(p: vec3, n: vec3, self_row: u32, samples: u32, pixel: u32, sample_index: u32, sc: SceneBufs) -> f32:
    """1 − hits/tests over uniform sphere directions flipped into the hemisphere, unlimited distance."""
    hits = 0.0
    for i in range(samples):
        d = uniform_sphere(rand01(pixel, sample_index, u32(10) + 2 * i), rand01(pixel, sample_index, u32(11) + 2 * i))
        if dot(d, n) < 0.0:
            d = d * -1.0
        h = trace(p, d, 1.0e-5, INF, u32(TRACE_ANY), self_row, sc)
        if h.prim != NO_HIT:
            hits += 1.0
    return 1.0 - hits / f32(max(samples, u32(1)))


@func
def phong_specular(n: vec3, to_light: vec3, rd: vec3, ks: f32) -> f32:
    dl = dot(n, to_light)  # deliberately unnormalised, as in 1.5
    if dl < 0.1:
        return 0.0
    r = normalize(n * (2.0 * dl) - to_light)
    s = -dot(r, normalize(rd))
    if s < 0.1:
        return 0.0
    return max(ks * pow(s, 50.0), 0.0)


@func
def classic_light(
    h: Hit, p: vec3, rd: vec3, level: u32, ao_samples: u32, pixel: u32, sample_index: u32, sc: SceneBufs
) -> f32:
    m = sc.prim_u[h.prim * PRIM_U + 1] * MAT_F
    row = sc.prim_u[h.prim * PRIM_U + 2]
    to_light = cfg3(sc.cfg, LIGHT_POS) - p
    diffuse = max(sc.mat_f[m + M_LEGACY_DIFFUSE] * dot(h.normal, normalize(to_light)), 0.0)
    spec = phong_specular(h.normal, to_light, rd, sc.mat_f[m + M_LEGACY_SPECULAR])
    ao = 1.0
    if level == 0:
        ao = classic_ao(p, h.normal, row, ao_samples, pixel, sample_index, sc)
    ambient = sc.mat_f[m + M_LEGACY_AMBIENT] * ao
    if sc.cfg[SHADOWS] > 0.0:
        dist = length(to_light)
        flags = u32(TRACE_ANY) | u32(TRACE_OPAQUE)
        shadow = trace(p, to_light * (1.0 / dist), 1.0e-5 * dist, dist, flags, row, sc)
        if shadow.prim != NO_HIT:
            return max(ambient, 0.0)
    return max(diffuse + spec + ambient, 0.0)


@func
def classic_radiance(
    o: vec3, d: vec3, max_depth: u32, ao_samples: u32, pixel: u32, sample_index: u32, sc: SceneBufs
) -> vec3:
    """Display-space colour of one camera sample."""
    background = srgb_encode(cfg3(sc.cfg, BACKGROUND))
    result = vec3(0.0)
    weight = 1.0
    ro = o
    rd = d
    exclude = u32(NO_HIT)
    for level in range(max_depth + 1):
        h = trace(ro, rd, 1.0e-7, INF, u32(0), exclude, sc)
        if h.prim == NO_HIT:
            return result + background * weight
        p = ro + rd * h.t
        s = surface_at(sc, h.prim)
        alpha = sc.prim_f[h.prim * PRIM_F + 15]
        r = sc.mat_f[sc.prim_u[h.prim * PRIM_U + 1] * MAT_F + M_LEGACY_REFLECTION]
        light = classic_light(h, p, rd, u32(level), ao_samples, pixel, sample_index, sc)
        result = result + srgb_encode(s.base) * (weight * light * alpha * (1.0 - r))
        w_through = (1.0 - r) * (1.0 - alpha)
        total = w_through + r
        if total <= 0.0:
            return result
        weight = weight * total
        exclude = sc.prim_u[h.prim * PRIM_U + 2]
        ro = p
        if rand01(pixel, sample_index, u32(64) + u32(level)) * total >= w_through:
            rd = rd - h.normal * (2.0 * dot(h.normal, rd))
    return result + background * weight
