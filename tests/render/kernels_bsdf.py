"""Test kernels that expose the principled BSDF's sampling and pdf to the host (χ² tests)."""

from __future__ import annotations

from structura.kernels.skl import Buf, BufRW, f32, kernel, u32, uvec3, vec3
from structura.render.kernels.bsdf import bsdf_eval, bsdf_sample, principled_setup
from structura.render.kernels.sampling import rand01
from structura.render.kernels.surface import Surface


@kernel(workgroup=(64, 1, 1))
def bsdf_samples(
    gid: uvec3, n: u32, front: u32, tangent: f32, wo_x: f32, wo_y: f32, wo_z: f32, mat_f: Buf[f32], result: BufRW[f32]
) -> None:
    """result[4i:4i+4] = sampled direction wi and the mixture pdf bsdf_eval reports for it."""
    i = gid.x
    if i >= n:
        return
    wo = vec3(wo_x, wo_y, wo_z)
    s = Surface(vec3(0.9, 0.6, 0.3), 1.0, vec3(0.0), u32(0))
    bs = principled_setup(mat_f, s, wo, front, 0.0, tangent)
    wi = bsdf_sample(bs, wo, rand01(i, u32(1), u32(0)), rand01(i, u32(1), u32(1)), rand01(i, u32(1), u32(2)))
    v = bsdf_eval(bs, wo, wi)
    result[i * 4] = wi.x
    result[i * 4 + 1] = wi.y
    result[i * 4 + 2] = wi.z
    result[i * 4 + 3] = v.pdf


@kernel(workgroup=(64, 1, 1))
def bsdf_pdfs(
    gid: uvec3,
    n: u32,
    front: u32,
    tangent: f32,
    wo_x: f32,
    wo_y: f32,
    wo_z: f32,
    mat_f: Buf[f32],
    dirs: Buf[f32],
    result: BufRW[f32],
) -> None:
    """result[i] = pdf of direction dirs[3i:3i+3]; result[n + i] = luminance-free f·cos (x channel)."""
    i = gid.x
    if i >= n:
        return
    wo = vec3(wo_x, wo_y, wo_z)
    s = Surface(vec3(0.9, 0.6, 0.3), 1.0, vec3(0.0), u32(0))
    bs = principled_setup(mat_f, s, wo, front, 0.0, tangent)
    v = bsdf_eval(bs, wo, vec3(dirs[i * 3], dirs[i * 3 + 1], dirs[i * 3 + 2]))
    result[i] = v.pdf
    result[n + i] = v.f.x
