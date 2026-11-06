"""First-hit AOVs (docs/09 §6): albedo, shading normal, depth, coverage, instance and material ids, for the
render view, multi-layer EXR and the denoiser. A separate kernel (its own module) run once per render with a
few jittered samples, so the beauty pass is untouched. Per pixel AOV_F floats (sums over the samples):
  [0:3] albedo   [3:6] world normal   [6] depth   [7] hits   [8] first instance row + 1   [9] material + 1
"""

from __future__ import annotations

from structura.kernels.skl import BufRW, f32, kernel, u32, uvec3

from .buffers import SceneBufs
from .camera import camera_ray
from .passes import pixel_sample
from .sampling import rand01
from .scene import NO_HIT, PRIM_U, trace
from .surface import surface_at

AOV_F = 10


@kernel(workgroup=(8, 8, 1))
def aov_pass(gid: uvec3, width: u32, height: u32, sample_base: u32, spp: u32, sc: SceneBufs, aov: BufRW[f32]) -> None:
    if gid.x >= width or gid.y >= height:
        return
    pixel = gid.x + gid.y * width
    at = pixel * AOV_F
    for k in range(spp):
        s = sample_base + k
        ps = pixel_sample(sc, pixel, s)
        sx = ((f32(gid.x) + ps.x) / f32(width)) * 2.0 - 1.0
        sy = 1.0 - ((f32(gid.y) + ps.y) / f32(height)) * 2.0
        ray = camera_ray(sc.cfg, sx, sy, rand01(pixel, s, u32(2)), rand01(pixel, s, u32(3)))
        h = trace(ray.o, ray.d, 0.0, 3.0e38, u32(0), u32(NO_HIT), sc)
        if h.prim == NO_HIT:
            continue
        surf = surface_at(sc, h.prim)
        aov[at] = aov[at] + surf.base.x
        aov[at + 1] = aov[at + 1] + surf.base.y
        aov[at + 2] = aov[at + 2] + surf.base.z
        aov[at + 3] = aov[at + 3] + h.normal.x
        aov[at + 4] = aov[at + 4] + h.normal.y
        aov[at + 5] = aov[at + 5] + h.normal.z
        aov[at + 6] = aov[at + 6] + h.t
        aov[at + 7] = aov[at + 7] + 1.0
        if aov[at + 8] == 0.0:
            aov[at + 8] = f32(sc.prim_u[h.prim * PRIM_U + 2] + 1)
            aov[at + 9] = f32(sc.prim_u[h.prim * PRIM_U + 1] + 1)
