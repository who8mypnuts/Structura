"""Pack a MaterialTable into the flat 'mat_f' buffer (layout: render/kernels/layout.py)."""

from __future__ import annotations

import math

import numpy as np

from ..core.color import srgb_to_linear
from ..core.scene.material import Material
from ..core.scene.material_library import MaterialTable
from .kernels import layout as lay

FAR = 1.0e30


def _linear(rgb: tuple[float, ...]) -> np.ndarray:
    return srgb_to_linear(np.asarray(rgb, np.float32))


def pack_material(m: Material) -> np.ndarray:
    r = np.zeros(lay.MAT_F, np.float32)
    fixed_base = not m.uses_state_color
    r[lay.M_BASE : lay.M_BASE + 3] = _linear(m.base) if fixed_base else 1.0  # type: ignore[arg-type]
    r[lay.M_BASE_STATE] = 0.0 if fixed_base else 1.0
    r[lay.M_METALLIC], r[lay.M_ROUGHNESS], r[lay.M_SPECULAR], r[lay.M_IOR] = (
        m.metallic,
        m.roughness,
        m.specular,
        max(m.ior, 1.0001),
    )
    r[lay.M_TRANSMISSION], r[lay.M_TRANS_ROUGHNESS] = m.transmission, m.transmission_roughness
    r[lay.M_COAT], r[lay.M_COAT_ROUGHNESS] = m.coat, m.coat_roughness
    emission = m.emission_rgb
    r[lay.M_EMISSION : lay.M_EMISSION + 3] = (_linear(emission) if emission else 1.0) * m.emission_strength
    r[lay.M_EMISSION_STATE] = 0.0 if emission else 1.0
    r[lay.M_EMISSION_STRENGTH] = m.emission_strength
    r[lay.M_OPACITY] = -1.0 if m.uses_state_alpha else float(m.opacity)
    r[lay.M_ATTENUATION : lay.M_ATTENUATION + 3] = _linear(m.attenuation_color)
    r[lay.M_ATTENUATION_DIST] = FAR if math.isinf(m.attenuation_distance) else m.attenuation_distance
    r[lay.M_LEGACY_AMBIENT], r[lay.M_LEGACY_DIFFUSE] = m.legacy_ambient, m.legacy_diffuse
    r[lay.M_LEGACY_SPECULAR], r[lay.M_LEGACY_REFLECTION] = m.legacy_specular, m.legacy_reflection
    r[lay.M_MODEL], r[lay.M_THIN] = int(m.model), float(m.thin_walled)
    r[lay.M_ANISOTROPY], r[lay.M_ANISO_ROTATION] = m.anisotropy, m.anisotropy_rotation
    return r


def pack_materials(table: MaterialTable) -> np.ndarray:
    """float32[M, MAT_F] (at least one default record)."""
    records = [pack_material(m) for m in table.materials] or [pack_material(Material())]
    return np.stack(records)
