"""Material presets and per-tag resolution with Structure Synth's raytracer keys (docs/07 §3)."""

from __future__ import annotations

import pytest

from structura.core.scene.material import Material, MaterialModel, material_from_dict, presets
from structura.core.scene.material_library import resolve_materials


def test_all_documented_presets_exist() -> None:
    names = {
        "matte", "plastic", "glossy", "clay", "ceramic", "rubber", "metal", "chrome", "gold", "copper",
        "brushed-metal", "glass", "frosted-glass", "tinted-glass", "mirror", "emissive", "neon", "ao",
        "constant", "wireframe", "shiny", "legacy",
    }  # fmt: skip
    assert set(presets()) == names
    assert presets()["neon"].model == MaterialModel.CONSTANT


def test_unknown_material_fields_are_rejected() -> None:
    with pytest.raises(ValueError, match="shininess"):
        material_from_dict("x", {"shininess": 3})


def test_legacy_keys_apply_to_the_default_class_or_one_tag() -> None:
    keys = [("phong", "0.2,0.9,0.1"), ("shiny::reflection", "0.5"), ("samples", "6")]
    table = resolve_materials(("", "shiny", "dull"), keys)
    default, shiny, dull = (table.materials[i] for i in table.by_tag)
    assert (default.legacy_ambient, default.legacy_diffuse, default.legacy_specular) == (0.2, 0.9, 0.1)
    assert shiny.legacy_reflection == 0.5 and shiny.legacy_ambient == 0.6  # tags start from 1.5's defaults
    assert shiny.coat == 0.5 and shiny.coat_roughness == 0.0  # the physically based equivalent
    assert dull == Material(name="dull")


def test_tag_presets_and_declared_materials() -> None:
    declared = {"mine": Material(name="mine", metallic=1.0)}
    table = resolve_materials(("", "glass", "mine"), [], declared, tag_presets=True)
    assert table.materials[table.by_tag[1]].transmission == 1.0
    assert table.materials[table.by_tag[2]].metallic == 1.0
    assert resolve_materials(("glass",), []).materials[0].transmission == 0.0  # v1: presets are opt-in
