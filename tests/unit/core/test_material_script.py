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


def test_every_panel_field_round_trips_through_a_block() -> None:
    glass = replace(
        presets()["glass"], name="tint", transmission_roughness=0.3, attenuation_color=(1.0, 0.5, 0.0),
        attenuation_distance=2.5, thin_walled=True, anisotropy=-0.4, anisotropy_rotation=0.25, opacity=0.8,
    )  # fmt: skip
    text = material_text(glass, "glass")
    for line in ("transmission_roughness 0.3", "attenuation_color #ff8000", "attenuation_distance 2.5",
                 "thin_walled true", "anisotropy -0.4", "anisotropy_rotation 0.25", "opacity 0.8"):  # fmt: skip
        assert line in text
    built = build_scene(compile_script(f"#version 2\n{text}\nbox::tint\n").program).scene.declarations
    assert built is not None
    back = built.materials["tint"]
    assert (back.transmission_roughness, back.attenuation_distance, back.thin_walled) == (0.3, 2.5, True)
    assert (back.anisotropy, back.anisotropy_rotation, back.opacity) == (-0.4, 0.25, 0.8)


def test_the_viewport_approximates_materials() -> None:
    from structura.core.scene.material_look import material_look  # noqa: PLC0415

    text = ("#version 2\nmaterial g { preset glass }\nmaterial lamp { emission #ffcc00 5 }\n"
            "{ color #336 } box::g\n{ x 2 color #336 } box::lamp\n{ x 4 color #336 } box\n")  # fmt: skip
    scene = build_scene(compile_script(text).program).scene
    looked = material_look(scene).rgba
    assert looked[0, 3] < 0.5 and looked[0, :3].min() > 0.6  # glass: pale and see-through
    assert looked[1, 0] > 0.9 and looked[1, 2] < 0.5  # emission: its own colour
    assert (looked[2] == scene.rgba[2]).all()  # the default material: the structure colour
    v1 = build_scene(compile_script("box::glass\n").program).scene
    assert material_look(v1) is v1  # v1 scripts are shown as authored
