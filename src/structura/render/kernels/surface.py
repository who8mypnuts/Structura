"""Per-hit surface lookup: instance colour/alpha combined with the material record (docs/07 §3)."""

from __future__ import annotations

from structura.kernels.skl import Buf, f32, func, mix, struct, u32, vec3

from .buffers import SceneBufs
from .layout import M_BASE, M_BASE_STATE, M_EMISSION, M_EMISSION_STATE, M_OPACITY, MAT_F
from .scene import PRIM_F, PRIM_U


@struct
class Surface:
    base: vec3  # linear base colour
    alpha: f32  # coverage (instance alpha or material opacity)
    emission: vec3  # emitted radiance
    mat: u32  # material record offset into mat_f


@func
def mat_rgb(mat_f: Buf[f32], at: u32) -> vec3:
    return vec3(mat_f[at], mat_f[at + 1], mat_f[at + 2])


@func
def surface_at(sc: SceneBufs, prim: u32) -> Surface:
    pb = prim * PRIM_F
    m = sc.prim_u[prim * PRIM_U + 1] * MAT_F
    state = vec3(sc.prim_f[pb + 12], sc.prim_f[pb + 13], sc.prim_f[pb + 14])
    base = mix(mat_rgb(sc.mat_f, m + M_BASE), state, sc.mat_f[m + M_BASE_STATE])
    emission = mat_rgb(sc.mat_f, m + M_EMISSION) * mix(vec3(1.0), state, sc.mat_f[m + M_EMISSION_STATE])
    opacity = sc.mat_f[m + M_OPACITY]
    alpha = sc.prim_f[pb + 15] if opacity < 0.0 else opacity
    return Surface(base, alpha, emission, m)
