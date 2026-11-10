"""Stochastic opacity for the first-hit passes ('preview', 'ao', the AOV pass): a camera ray passes through an
instance with probability 1 − alpha, once per instance, exactly like the path tracer (kernels/path.py), so a
transparent structure looks see-through in every integrator and the denoiser's guides match the image."""

from __future__ import annotations

from structura.kernels.skl import INF, func, u32, vec3

from .buffers import SceneBufs
from .hit import Hit, miss
from .sampling import rand01
from .scene import NO_HIT, PRIM_U, trace
from .surface import surface_at

PASS_LIMIT = 16  # see-through instances a ray may cross before it gives up
OPACITY_DIM = 200  # random dimensions OPACITY_DIM … OPACITY_DIM + PASS_LIMIT (clear of the integrators' own)


@func
def visible_hit(o: vec3, d: vec3, pixel: u32, sample_index: u32, sc: SceneBufs) -> Hit:
    """The first surface the ray stops at; ``t`` is measured from ``o`` (a miss when it passes everything)."""
    ro = o
    travelled = 0.0
    exclude = u32(NO_HIT)
    for step in range(PASS_LIMIT):
        h = trace(ro, d, 0.0, INF, u32(0), exclude, sc)
        if h.prim == NO_HIT:
            return h
        alpha = surface_at(sc, h.prim).alpha
        if alpha >= 1.0 or rand01(pixel, sample_index, u32(OPACITY_DIM) + u32(step)) < alpha:
            return Hit(travelled + h.t, h.normal, h.prim, h.front)
        travelled = travelled + h.t
        ro = ro + d * h.t
        exclude = sc.prim_u[h.prim * PRIM_U + 2]
    return miss()
