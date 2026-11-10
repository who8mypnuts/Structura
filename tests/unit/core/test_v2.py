"""EisenScript v2 front passes: blocks, '( expr )', '#param' (docs/05 §9)."""

from __future__ import annotations

import pytest

from structura.core.build.api import build_scene
from structura.core.lang.analysis import analyze
from structura.core.lang.api import compile_script
from structura.core.lang.diagnostics import ParseError
from structura.core.lang.v2.blocks import extract_blocks
from structura.render.api import script_settings
from structura.render.config import scene_frame

SCRIPT = """#version 2
#param n int = 4 range 1..20
material shiny { preset metal roughness 0.1 emission #ff8800 2 }
light key { type sun direction [0 -1 0] intensity 2 }
environment { type color color #ffffff }
camera { position [0 2 10] target [0 0 0] fov 30 }
render { integrator ao samples 16 size 320x200 }
n * { x (1 + 0.5) rz (90 / n) } box::shiny
"""


def test_blocks_become_declarations_and_disappear_from_the_text() -> None:
    extracted = extract_blocks(SCRIPT)
    assert "material" not in extracted.text and extracted.text.count("\n") == SCRIPT.count("\n")
    shiny = extracted.declarations.materials["shiny"]
    assert shiny.metallic == 1.0 and shiny.roughness == 0.1 and shiny.emission_strength == 2.0
    assert extracted.declarations.lights[0].type == "sun"


def test_v2_scripts_build_with_expressions_and_param_sliders() -> None:
    compiled = compile_script(SCRIPT)
    scene = build_scene(compiled.program).scene
    assert len(scene) == 4 and compiled.parameters[0].name == "n"
    assert scene.declarations is not None and "shiny" in scene.declarations.materials
    assert abs(float(scene.xform[0, 0, 0]) - 0.9238795) < 1e-6  # 'rz (90 / n)' = 22.5° with n = 4
    assert len(build_scene(compile_script(SCRIPT, params={"n": 7}).program).scene) == 7


def test_blocks_drive_render_settings_and_camera() -> None:
    scene = build_scene(compile_script(SCRIPT).program).scene
    settings = script_settings(scene)
    assert (settings.integrator, settings.samples, settings.width, settings.height) == ("ao", 16, 320, 200)
    assert settings.sun_direction == (0.0, 1.0, 0.0) and settings.backdrop_sky
    assert settings.sky_top == settings.sky_bottom == (1.0, 1.0, 1.0)
    from structura.core.scene.settings import settings_from_events  # noqa: PLC0415

    frame = scene_frame(settings_from_events(scene.events), settings, scene.xform[0, :, 3], scene.xform[0, :, 3] + 1,
                        scene.declarations)  # fmt: skip
    assert frame.camera.eye == (0.0, 2.0, 10.0) and frame.camera.fov_y_deg == 30.0


def test_expression_errors_are_diagnostics_with_positions() -> None:
    text = "#version 2\n{ x (1 / 0) } box\n"
    with pytest.raises(ParseError):
        compile_script(text)
    analysis = analyze(text)
    assert analysis.diagnostics[-1].code == "E016" and analysis.diagnostics[-1].span is not None


def test_v1_scripts_are_untouched() -> None:
    text = "material shiny { roughness 0.1 }\n"  # not a v2 script: 'material' is just a rule call here
    assert compile_script("{ x 1 } box").program.declarations is None
    with pytest.raises(ParseError):
        compile_script(text)


def test_rand_in_expressions_draws_like_random_brackets() -> None:
    from structura.core.build.api import build_scene  # noqa: PLC0415
    from structura.core.lang.analysis import analyze  # noqa: PLC0415
    from structura.core.lang.api import compile_script  # noqa: PLC0415

    def x_of(text: str) -> float:
        return float(build_scene(compile_script(text, seed=3).program, 3).scene.xform[0, 0, 3])

    drawn = x_of("#version 2\n{ x (rand(2, 4) * 10) } box\n")
    assert 20 <= drawn <= 40 and drawn == x_of("#version 2\n{ x (random[2,4] * 10) } box\n")
    assert [d.code for d in analyze("#version 2\n{ x (rand(1, pi)) } box\n").diagnostics] == ["E016"]
