"""The special material models (docs/10 §3.2): 'wireframe', 'ao' and the debug views, shaded unlit at the
first surface they are seen on, in the 'path', 'preview' and 'ao' integrators alike. Also the ambient-occlusion
estimate these integrators share.

  wireframe          the instance colour on the edges of its unit cube (boxes, grids, v2 solids) or triangle,
                     a dark version of it elsewhere
  ao                 the instance colour × ambient occlusion (Sunflow's AmbientOcclusionShader)
  debug_normal       the world normal as a colour          debug_id       a colour per instance
  debug_uv           object-space x, y                      debug_generation   the build generation, blue → red
  debug_gray         a grey facing ratio (Sunflow's QuickGrayShader)
"""

from __future__ import annotations

from structura.kernels.skl import Buf, abs, dot, f32, fract, func, max, min, u32, vec3

from .buffers import SceneBufs
from .hit import Hit, to_object
from .layout import AO_DIST, EPS, M_MODEL, MAX_GENERATION
from .lights import offset
from .sampling import cosine_hemisphere, hash_u32, rand01
from .scene import NO_HIT, PRIM_F, PRIM_U, RK_TRIANGLE, TRACE_ANY, trace
from .shapes import on_grid_edge
from .surface import Surface

MODEL_WIREFRAME, MODEL_AO, MODEL_DEBUG_GRAY = 2, 3, 8  # core.scene.material.MaterialModel
MODEL_DEBUG_NORMAL, MODEL_DEBUG_ID, MODEL_DEBUG_UV, MODEL_DEBUG_GENERATION = 4, 5, 6, 7
WIRE_WIDTH = 0.03  # of the unit cube's edge (object space), or of a triangle's barycentric range
WIRE_FILL = 0.12  # brightness of the faces between the lines


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
def is_special(mat_f: Buf[f32], mat: u32) -> bool:
    model = mat_f[mat + M_MODEL]
    return model >= f32(MODEL_WIREFRAME) and model <= f32(MODEL_DEBUG_GRAY)


@func
def triangle_edge(sc: SceneBufs, prim: u32, p: vec3) -> bool:
    """p lies within WIRE_WIDTH (barycentric) of an edge of the triangle primitive."""
    tb = sc.prim_u[prim * PRIM_U + 3] * 9
    a = vec3(sc.tri_f[tb], sc.tri_f[tb + 1], sc.tri_f[tb + 2])
    e1 = vec3(sc.tri_f[tb + 3], sc.tri_f[tb + 4], sc.tri_f[tb + 5]) - a
    e2 = vec3(sc.tri_f[tb + 6], sc.tri_f[tb + 7], sc.tri_f[tb + 8]) - a
    q = p - a
    d11 = dot(e1, e1)
    d12 = dot(e1, e2)
    d22 = dot(e2, e2)
    det = max(d11 * d22 - d12 * d12, 1.0e-20)
    v = (d22 * dot(q, e1) - d12 * dot(q, e2)) / det
    w = (d11 * dot(q, e2) - d12 * dot(q, e1)) / det
    return min(min(v, w), 1.0 - v - w) < WIRE_WIDTH


@func
def wireframe(sc: SceneBufs, h: Hit, p: vec3, s: Surface) -> vec3:
    if sc.prim_u[h.prim * PRIM_U] == u32(RK_TRIANGLE):
        edge = triangle_edge(sc, h.prim, p)
    else:
        edge = on_grid_edge(to_object(sc.prim_f, h.prim * PRIM_F, p, 1.0), WIRE_WIDTH)
    return s.base if edge else s.base * WIRE_FILL


@func
def id_colour(row: u32) -> vec3:
    k = hash_u32(row * u32(2654435761) + u32(12345))
    return vec3(f32(k & u32(255)), f32((k >> 8) & u32(255)), f32((k >> 16) & u32(255))) * (1.0 / 255.0)


@func
def heat(t: f32) -> vec3:
    """Blue → green → red for t in 0..1."""
    x = max(0.0, min(t, 1.0))
    return vec3(x, 1.0 - abs(2.0 * x - 1.0), 1.0 - x)


@func
def debug_view(sc: SceneBufs, h: Hit, p: vec3, rd: vec3, model: f32) -> vec3:
    """The debug_* models (script-only diagnostic looks)."""
    if model == f32(MODEL_DEBUG_NORMAL):
        return h.normal * 0.5 + vec3(0.5)
    if model == f32(MODEL_DEBUG_ID):
        return id_colour(sc.prim_u[h.prim * PRIM_U + 2])
    if model == f32(MODEL_DEBUG_UV):
        q = to_object(sc.prim_f, h.prim * PRIM_F, p, 1.0)
        return vec3(fract(q.x), fract(q.y), 0.0)
    if model == f32(MODEL_DEBUG_GENERATION):
        return heat(sc.prim_f[h.prim * PRIM_F + 23] / max(sc.cfg[MAX_GENERATION], 1.0))
    return vec3(0.1 + 0.8 * abs(dot(h.normal, rd)))


@func
def special_radiance(
    sc: SceneBufs, h: Hit, p: vec3, rd: vec3, s: Surface, pixel: u32, sample_index: u32, dim: u32
) -> vec3:
    """The unlit colour of a special model (is_special) at the hit point p of a ray with direction rd."""
    model = sc.mat_f[s.mat + M_MODEL]
    if model == f32(MODEL_WIREFRAME):
        return wireframe(sc, h, p, s)
    if model == f32(MODEL_AO):
        return s.base * ambient_occlusion(p, h.normal, u32(1), sc.cfg[AO_DIST], pixel, sample_index, dim, sc)
    return debug_view(sc, h, p, rd, model)
