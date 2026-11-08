"""Material → v2 script text (docs/14 §3 "Write as v2 material block", docs/05 §9.3).

``material_text`` writes only what differs from the starting preset (or the default material), so blocks stay
short and readable. ``with_material`` replaces the script's block of that name, or adds one with the other
declarations (script_blocks.put_block).
"""

from __future__ import annotations

from dataclasses import fields

from .material import STATE, Material, MaterialModel, presets
from .script_blocks import put_block

WRITTEN = ("model", "metallic", "roughness", "specular", "ior", "transmission", "transmission_roughness", "coat",
           "coat_roughness", "anisotropy", "thin_walled")  # fmt: skip


def _number(x: float) -> str:
    return f"{float(x):.4g}"


def _colour(value: str | tuple[float, float, float]) -> str:
    if value == STATE:
        return STATE
    r, g, b = (min(255, max(0, round(float(c) * 255))) for c in value)
    return f"#{r:02x}{g:02x}{b:02x}"


def _differs(material: Material, start: Material, name: str) -> bool:
    return bool(getattr(material, name) != getattr(start, name))


def material_text(material: Material, preset: str = "") -> str:
    start = presets().get(preset, Material())
    lines = [f"material {material.name} {{"] + ([f"  preset {preset}"] if preset in presets() else [])
    if material.base != start.base:
        lines.append(f"  base {_colour(material.base)}")
    for name in WRITTEN:
        if _differs(material, start, name):
            value = getattr(material, name)
            text = value.name.lower() if isinstance(value, MaterialModel) else str(value).lower() \
                if isinstance(value, bool) else _number(value)  # fmt: skip
            lines.append(f"  {name} {text}")
    if (material.emission, material.emission_strength) != (start.emission, start.emission_strength):
        lines.append(f"  emission {_colour(material.emission)} {_number(material.emission_strength)}")
    if material.opacity != start.opacity:
        lines.append(f"  opacity {material.opacity if material.opacity == STATE else _number(material.opacity)}")  # type: ignore[arg-type]
    return "\n".join([*lines, "}"])


def with_material(text: str, material: Material, preset: str = "") -> str:
    return put_block(text, "material", material.name, material_text(material, preset))


def material_fields() -> tuple[str, ...]:
    return tuple(f.name for f in fields(Material))
