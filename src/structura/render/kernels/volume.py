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
    """Returns the transmittance over a distance inside a material (Beer–Lambert).

    Args:
        mat_f: The material records.
        mat: Offset of the material's record.
        t: The distance travelled inside, in world units.

    Returns:
        Per-channel transmittance; 1 for clear, thin-walled or opaque materials.
    """
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
    """Returns the absorption of a path segment that ends on a primitive.

    Args:
        mat_f: The material records.
        prim_u: The primitives' int records (their material).
        prim: The primitive the segment ends on.
        front: 1 when the segment hit the primitive from outside (no absorption), 0 from inside.
        t: The segment's length.

    Returns:
        Per-channel transmittance of the segment.
    """
    if front != u32(0):
        return vec3(1.0)
    return absorption(mat_f, prim_u[prim * PRIM_U + 1] * MAT_F, t)
