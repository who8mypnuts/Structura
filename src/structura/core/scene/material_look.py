"""An approximation of v2 materials in the viewport's authored colours (docs/08 §5; PLAN QoL-5).

The preview engine shades every instance with its colour and alpha, so a glass, tinted or glowing material
would look like the plain structure colour until it is rendered. Here each instance's RGBA is adjusted for its
material once per build: a fixed base colour replaces the structure colour, a fixed opacity replaces the
alpha, transmissive materials become pale and see-through (the preview's OIT draws them), and emissive ones
take their emission colour, brightened. Renders and exports never see this."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from .ir import SceneIR
from .material import STATE, Material
from .material_library import resolve_materials
from .settings import settings_from_events

GLASS_LIGHTEN = 0.35  # towards white, at full transmission
GLASS_ALPHA = 0.35  # what is left of the alpha at full transmission
GLOW_LIGHTEN = 0.3


def _looked(material: Material, rgba: np.ndarray) -> np.ndarray:
    out = rgba.copy()
    if material.base != STATE:
        out[:, :3] = material.base
    if not isinstance(material.opacity, str):  # a fixed opacity (not 'state')
        out[:, 3] = float(material.opacity)
    glass = material.transmission * (1.0 - material.metallic)
    if glass > 0.0:
        out[:, :3] += (1.0 - out[:, :3]) * (GLASS_LIGHTEN * glass)
        out[:, 3] *= 1.0 - (1.0 - GLASS_ALPHA) * glass
    if material.emission_strength > 0.0:
        glow = out[:, :3] if material.emission_rgb is None else np.asarray(material.emission_rgb, np.float32)
        out[:, :3] = glow + (1.0 - glow) * GLOW_LIGHTEN
    return out


def material_look(scene: SceneIR) -> SceneIR:
    """``scene`` with its colours adjusted for its v2 materials (unchanged for v1 scripts)."""
    if scene.declarations is None or not len(scene):
        return scene
    raytracer = settings_from_events(scene.events).raytracer
    table = resolve_materials(scene.tags, raytracer, scene.declarations.materials, tag_presets=True)
    of_row = table.by_tag[scene.tag]
    rgba = np.array(scene.rgba, np.float32)
    for index, material in enumerate(table.materials):
        rows = of_row == index
        if rows.any() and material != Material(name=material.name):
            rgba[rows] = _looked(material, rgba[rows])
    return replace(scene, rgba=np.clip(rgba, 0.0, 1.0))
