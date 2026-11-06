"""Materials (docs/07 §3): the principled parameter set shared by the renderers and the exporters.

The fields deliberately mirror UsdPreviewSurface, glTF PBR and Blender's Principled BSDF, so export is a
renaming. ``legacy_*`` fields carry Structure Synth 1.5's Phong model for the ``classic`` integrator.
"""

from __future__ import annotations

import math
import tomllib
from dataclasses import dataclass, fields, replace
from enum import IntEnum
from functools import cache
from pathlib import Path
from typing import Any

RGB = tuple[float, float, float]
PRESETS_FILE = Path(__file__).resolve().parent / "materials.toml"


class MaterialModel(IntEnum):
    PRINCIPLED = 0
    CONSTANT = 1
    WIREFRAME = 2
    AO = 3
    DEBUG_NORMAL = 4
    DEBUG_ID = 5
    DEBUG_UV = 6
    DEBUG_GENERATION = 7
    DEBUG_GRAY = 8


STATE = "state"  # base / opacity taken from the instance's rgba


@dataclass(frozen=True)
class Material:
    name: str = "default"
    model: MaterialModel = MaterialModel.PRINCIPLED
    base: str | RGB = STATE
    metallic: float = 0.0
    roughness: float = 0.5
    specular: float = 0.5  # dielectric F0 scale (0.5 → 4% at ior 1.5)
    ior: float = 1.5
    transmission: float = 0.0
    transmission_roughness: float = 0.0
    emission: str | RGB = STATE  # colour of the light emitted at emission_strength
    emission_strength: float = 0.0
    opacity: str | float = STATE
    coat: float = 0.0
    coat_roughness: float = 0.03
    anisotropy: float = 0.0
    anisotropy_rotation: float = 0.0
    attenuation_color: RGB = (1.0, 1.0, 1.0)
    attenuation_distance: float = math.inf
    thin_walled: bool = False
    legacy_ambient: float = 0.6
    legacy_diffuse: float = 0.6
    legacy_specular: float = 0.6
    legacy_reflection: float = 0.0

    @property
    def uses_state_color(self) -> bool:
        return self.base == STATE

    @property
    def emission_rgb(self) -> RGB | None:
        """Fixed emission colour, or None when it follows the instance colour."""
        return None if self.emission == STATE else self.emission  # type: ignore[return-value]

    @property
    def uses_state_alpha(self) -> bool:
        return self.opacity == STATE


FIELD_NAMES = frozenset(f.name for f in fields(Material))


def _coerce(key: str, value: Any) -> Any:
    if key == "model":
        return MaterialModel[str(value).upper().replace("-", "_")]
    if isinstance(value, list):
        return tuple(float(v) for v in value)
    return value


def material_from_dict(name: str, data: dict[str, Any], base: Material | None = None) -> Material:
    unknown = set(data) - FIELD_NAMES - {"preset"}
    if unknown:
        raise ValueError(f"material {name!r}: unknown fields {sorted(unknown)}")
    start = base or Material()
    values = {k: _coerce(k, v) for k, v in data.items() if k != "preset"}
    return replace(start, name=name, **values)


@cache
def presets() -> dict[str, Material]:
    """The built-in presets (docs/10 §3.3), keyed by name."""
    table = tomllib.loads(PRESETS_FILE.read_text(encoding="utf-8"))
    return {name: material_from_dict(name, data) for name, data in table.items()}


def legacy_phong(material: Material, ambient: float, diffuse: float, specular: float) -> Material:
    """Apply 'set raytracer::[TAG::]phong [a,d,s]' and its principled migration (docs/10 §6.2)."""
    return replace(
        material,
        legacy_ambient=ambient,
        legacy_diffuse=diffuse,
        legacy_specular=specular,
        specular=0.5 * specular / 0.6,
        roughness=0.2 if specular > 0 else material.roughness,
    )


def legacy_reflection(material: Material, reflection: float) -> Material:
    """Apply 'set raytracer::[TAG::]reflection r': a clear coat for the physically based integrators."""
    return replace(material, legacy_reflection=reflection, coat=reflection, coat_roughness=0.0)
