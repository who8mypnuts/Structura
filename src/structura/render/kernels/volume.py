"""Absorption inside transmissive materials (Beer–Lambert; docs/10 §2.3 'Volumes').

A ray that reaches a surface from the inside (``Hit.front == 0``) has travelled through that primitive's
material for the whole segment, because every render primitive is a closed solid. Its throughput is scaled
by ``attenuation_color ^ (t / attenuation_distance)``: the colour is what white light becomes after exactly
that distance. No medium stack is needed, and thin-walled or opaque materials never absorb.
"""

from __future__ import annotations

from structura.kernels.skl import Buf, f32, func, max, pow, u32, vec3

from .layout import M_ATTENUATION, M_ATTENUATION_DIST, M_THIN, M_TRANSMISSION, MAT_F
from .scene import PRIM_U

NO_ABSORPTION = 1.0e29  # attenuation distances at least this large mean "clear" (render/materials.py FAR)


@func
def absorption(mat_f: Buf[f32], mat: u32, t: f32) -> vec3:
    """Transmittance over ``t`` world units inside the material record at ``mat``."""
    dist = mat_f[mat + M_ATTENUATION_DIST]
    if dist >= NO_ABSORPTION or mat_f[mat + M_TRANSMISSION] <= 0.0 or mat_f[mat + M_THIN] != 0.0:
        return vec3(1.0)
    k = t / max(dist, 1.0e-9)
    r = pow(max(mat_f[mat + M_ATTENUATION], 1.0e-6), k)
    g = pow(max(mat_f[mat + M_ATTENUATION + 1], 1.0e-6), k)
    b = pow(max(mat_f[mat + M_ATTENUATION + 2], 1.0e-6), k)
    return vec3(r, g, b)


@func
def exit_absorption(mat_f: Buf[f32], prim_u: Buf[u32], prim: u32, front: u32, t: f32) -> vec3:
    """The absorption of a path segment of length ``t`` that ends on ``prim`` (1 unless it hit it from inside)."""
    if front != u32(0):
        return vec3(1.0)
    return absorption(mat_f, prim_u[prim * PRIM_U + 1] * MAT_F, t)
