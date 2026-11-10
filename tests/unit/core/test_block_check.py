"""v2 block keys and values are checked against the language catalogue (PLAN Q2)."""

from __future__ import annotations

import pytest

from structura.core.build.api import build_scene
from structura.core.lang.analysis import analyze
from structura.core.lang.api import compile_script
from structura.core.lang.catalog import v2_blocks
from structura.core.lang.fixes import apply_edits, quick_fixes
from structura.core.lang.v2.block_check import known_keys, verdict
from structura.core.lang.v2.block_form import block_specs, block_text, entries_of, form_values
from structura.render.api import script_settings
from structura.render.kernels.layout import CAMERA_TYPES, LIGHT_TYPES
from structura.render.settings import DENOISERS, FILTER_NAMES, INTEGRATORS, SAMPLERS, SEQUENCES, VIEWS


def _codes(text: str) -> list[tuple[str, str]]:
    return [(d.code, d.message) for d in analyze(text).diagnostics]


def test_a_misspelt_key_is_reported_with_a_fix() -> None:
    text = "#version 2\ncamera { apreture 0.1 fov 30 }\nbox\n"
    found = [d for d in analyze(text).diagnostics if d.code == "W115"]
    assert found and "did you mean 'aperture'" in found[0].message
    assert text[found[0].span.start : found[0].span.end] == "apreture"  # type: ignore[union-attr]
    fixed = apply_edits(text, quick_fixes(text, found)[0].edits)
    assert "aperture 0.1" in fixed and not [d for d in analyze(fixed).diagnostics if d.code == "W115"]


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("light l { type pointt position [0 1 0] }", "E017"),
        ("material m { preset glas }", "E017"),
        ("material m { roughness abc }", "E017"),
        ("material m { metallic 2 }", "W117"),
        ("render { samples 12.5 }", "E017"),
        ("render { size 1920 }", "E017"),
        ("environment { type sunsky turbidity 20 }", "W117"),
        ("camera { position [0 1] }", "E017"),
    ],
)
def test_bad_values_are_reported(text: str, code: str) -> None:
    assert code in [c for c, _ in _codes(f"#version 2\n{text}\nbox\n")]


def test_bad_values_never_reach_the_renderer() -> None:
    scene = build_scene(compile_script("#version 2\nlight l { type pointt }\nmaterial m { roughness abc }\nbox::m\n")
                        .program).scene  # fmt: skip
    assert scene.declarations is not None
    assert not scene.declarations.lights  # an unknown light type is no light (it used to become a sun)
    assert scene.declarations.materials["m"].roughness == 0.5  # the default, not a string


def test_the_documented_v2_example_is_clean() -> None:
    text = ("#version 2\nmaterial shiny {\n  preset    plastic          # optional starting point\n  base      state\n"
            "  metallic  0.0\n  emission  #ffffff 0.0\n  opacity   state\n}\n"
            "light key  { type sun    direction [-1 -2 -1]  color #fff  intensity 3  angle 0.53 }\n"
            "light fill { type sphere position  [0 10 0]    radius 1    color #ffe  power 200 }\n"
            "environment { type sunsky  sun key  turbidity 3  ground #333 }\n"
            "camera { type perspective position [0 0 20] target [0 0 0] fov 35 aperture 0.05 focus auto blades 6 }\n"
            "render { integrator path samples 512 size 1920x1080 max-bounces 8 filter mitchell denoise auto view agx "
            "exposure 0.5 }\nbox::shiny\n")  # fmt: skip
    assert _codes(text) == []
    settings = script_settings(build_scene(compile_script(text).program).scene)
    assert (settings.view, settings.exposure, settings.denoise) == ("agx", 0.5, "auto")


def test_the_render_block_declares_a_look() -> None:
    text = '#version 2\nrender { look cinematic bloom 0.2 vignette 0.4 lut "grade.cube" }\nbox\n'
    assert _codes(text) == []
    post = script_settings(build_scene(compile_script(text).program).scene).post
    assert (post.bloom, post.vignette, post.lut, post.contrast) == (0.2, 0.4, "grade.cube", 1.15)
    assert [code for code, _ in _codes("#version 2\nrender { look dreamy bloom 5 }\nbox\n")] == ["E017", "W117"]


def test_the_catalogue_choices_match_the_renderer() -> None:
    render = {k.name: k.value for k in v2_blocks()["render"].keys}
    for key, names in (("integrator", INTEGRATORS), ("filter", FILTER_NAMES), ("sampler", SAMPLERS),
                       ("sequence", SEQUENCES), ("view", VIEWS), ("denoise", DENOISERS)):  # fmt: skip
        assert {c.strip() for c in render[key].split("|")} == set(names), key
    light = {k.name: k.value for k in v2_blocks()["light"].keys}["type"]
    assert {c.strip() for c in light.split("|")} == {"sun", *LIGHT_TYPES}
    camera = {k.name: k.value for k in v2_blocks()["camera"].keys}["type"]
    assert {c.strip() for c in camera.split("|")} == set(CAMERA_TYPES)


def test_environment_sun_picks_the_named_light() -> None:
    text = ("#version 2\nlight a { type sun direction [0 -1 0] }\nlight b { type sun direction [1 0 0] }\n"
            "environment { type sunsky sun b }\nbox\n")  # fmt: skip
    settings = script_settings(build_scene(compile_script(text).program).scene)
    assert settings.sun_vector == pytest.approx((-1.0, 0.0, 0.0))


def test_verdict_grammar() -> None:
    assert verdict("auto | number", "auto").ok and verdict("auto | number", 3.0).ok
    assert not verdict("auto | number", "far").ok
    assert verdict("[x y z]", (1.0, 2.0, 3.0)).ok and not verdict("[x y z]", (1.0, 2.0)).ok
    assert verdict("colour", "#fa0").ok and verdict("colour", "orange").ok and not verdict("colour", "bluish").ok
    outside = verdict("0..1", 1.5)
    assert outside.ok and not outside.in_range


def test_light_forms_round_trip() -> None:
    specs = block_specs("light", "spot")
    assert "direction" not in {s.key for s in specs} and "cone" in {s.key for s in specs}
    values = form_values(specs, {"type": "spot", "position": (1.0, 2.0, 3.0), "cone": 25.0, "color": "#ffcc80"})
    values["position"] = "[4 5 6]"  # edited as text
    entries = entries_of(specs, values, known_keys("light"))
    text = "#version 2\n" + block_text("light", "key", entries) + "\nbox\n"
    light = build_scene(compile_script(text).program).scene.declarations.lights[0]  # type: ignore[union-attr]
    assert (light.type, light.values["position"], light.values["cone"]) == ("spot", (4.0, 5.0, 6.0), 25.0)
