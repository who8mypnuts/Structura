"""The render kernels' buffer set: everything a ray needs, passed as one 'sc' argument (skl.bufset)."""

from __future__ import annotations

from structura.kernels.skl import Buf, bufset, f32, u32


@bufset
class SceneBufs:
    cfg: Buf[f32]  # per-render configuration (layout.py), then the pixel filter table
    prim_f: Buf[f32]  # primitive float records (render/pack.py)
    prim_u: Buf[u32]  # primitive int records: kind, material, instance row, triangle row
    tri_f: Buf[f32]  # world-space triangle corners
    node_f: Buf[f32]  # BVH node bounds (render/bvh.py)
    node_u: Buf[u32]  # BVH node links
    order: Buf[u32]  # BVH leaf order → primitive
    mat_f: Buf[f32]  # material records (render/materials.py)
    light_f: Buf[f32]  # point / sphere / spot / rect light records (render/lights.py)
    env_f: Buf[f32]  # environment map texels, linear RGB, then their importance-sampling CDFs (marginal, then
    #                  one conditional per row; render/environment.py)
    emit_f: Buf[f32]  # emissive primitives as lights, then their selection CDF by power (render/emitters.py)
    prim_emit: Buf[u32]  # primitive → its emitter record (NO_EMITTER if it does not emit)
    photon_f: Buf[f32]  # caustic photon map: hash table, then photons (render/photons.py)
