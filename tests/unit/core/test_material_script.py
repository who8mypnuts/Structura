"""Writing materials as v2 blocks (docs/05 §9.3)."""

from __future__ import annotations

from dataclasses import replace

from structura.core.build.api import build_scene
from structura.core.lang.api import compile_script
from structura.core.scene.material import Material, presets
from structura.core.scene.material_script import material_text, with_material


def test_only_the_differences_from_the_preset_are_written() -> None:
    gold = replace(presets()["gold"], name="bling", roughness=0.4)
    assert material_text(gold, "gold") == "material bling {\n  preset gold\n  roughness 0.4\n}"
    plain = replace(Material(), name="soft", base=(1.0, 0.5, 0.0), emission=(1.0, 1.0, 1.0), emission_strength=3.0)
    assert "base #ff8000" in material_text(plain) and "emission #ffffff 3" in material_text(plain)


def test_blocks_are_added_once_then_replaced_and_build_the_material() -> None:
    text = "#version 2\nmaterial other { roughness 0.2 }\nbox::bling\n"
    first = with_material(text, replace(presets()["gold"], name="bling", roughness=0.4), "gold")
    second = with_material(first, replace(presets()["gold"], name="bling", roughness=0.9), "gold")
    assert second.count("material bling") == 1 and "material other" in second
    assert second.index("material other") < second.index("material bling") < second.index("box::bling")
    built = build_scene(compile_script(second).program).scene.declarations
    assert built is not None and built.materials["bling"].roughness == 0.9 and built.materials["bling"].metallic == 1.0
