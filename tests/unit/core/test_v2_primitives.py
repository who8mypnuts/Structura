"""v2 primitives (cylinder, cone[r], torus[r], ellipsoid, tube[r]) and the 'mat' operator (docs/05 §9.3, §9.6)."""

from __future__ import annotations

import numpy as np
import pytest

from structura.core.build.api import build_scene
from structura.core.errors import BuildError, UnresolvedRuleError
from structura.core.geometry.tessellate import tessellate
from structura.core.lang.analysis import analyze
from structura.core.lang.api import compile_script
from structura.core.scene.ir import PrimitiveKind as K
from structura.core.scene.ir import SceneIR
from structura.preview.instances import preview_scene


def _build(text: str) -> SceneIR:
    return build_scene(compile_script(text).program).scene


def test_v2_primitives_build_with_their_parameters() -> None:
    scene = _build("#version 2\ncylinder\ncone\ncone[0.5]\ntorus\ntorus[0.3]\nellipsoid\ntube[0.2]\n")
    kinds = [K(k) for k in scene.kind]
    assert kinds == [K.CYLINDER, K.CONE, K.CONE, K.TORUS, K.TORUS, K.ELLIPSOID, K.TUBE]
    assert np.allclose(scene.params(np.arange(len(scene))), [0, 0, 0.5, 0.2, 0.3, 0, 0.2])


def test_v1_keeps_its_meaning() -> None:
    scene = _build("cylinder::gold\nbox")  # Structure Synth 1.5 counted a cylinder but drew nothing; Structura draws it
    assert [K(k) for k in scene.kind] == [K.CYLINDER, K.BOX] and scene.tags[scene.tag[0]] == "gold"
    assert K(_build("rule tube { box }\ntube").kind[0]) == K.BOX  # v2 names are free rule names in v1
    with pytest.raises(UnresolvedRuleError):
        compile_script("cone")


def test_bracket_primitives_take_tags_and_reject_bad_arguments() -> None:
    scene = _build("#version 2\ncone[0.5]::gold\ntriangle[0,0,0;1,0,0;0,1,0]::glass\n")
    assert [scene.tags[t] for t in scene.tag] == ["gold", "glass"] and K(scene.kind[1]) == K.TRIANGLE
    with pytest.raises(BuildError) as error:
        compile_script("#version 2\ncone[wide]\n")
    assert error.value.code == "E014"


def test_mat_is_inherited_and_an_explicit_tag_wins() -> None:
    text = "#version 2\n{ mat shiny } R\nrule R { box { x 1 } sphere::clay { x 2 mat dull } box }\n"
    scene = _build(text)
    assert [scene.tags[t] for t in scene.tag] == ["shiny", "clay", "dull"]
    assert analyze(text).ok


def test_mat_is_not_an_operator_in_v1() -> None:
    with pytest.raises(Exception, match="right bracket or an operator"):
        compile_script("{ mat shiny } box")


@pytest.mark.parametrize("call", ["cylinder", "cone[0.3]", "torus[0.25]", "ellipsoid", "tube[0.2]"])
def test_tessellation_fills_the_unit_cube(call: str) -> None:
    scene = _build(f"#version 2\n{{ s 2 }} {call}\n")
    mesh = tessellate(scene)
    assert mesh.triangles > 50 and np.allclose(np.linalg.norm(mesh.normals, axis=1), 1.0, atol=1e-4)
    lo, hi = mesh.positions.min(axis=0), mesh.positions.max(axis=0)
    assert np.all(lo >= -0.5 - 0.25) and np.all(hi <= 1.5 + 0.25)  # "s 2" about the cube centre; tube caps


def test_the_preview_draws_v2_shapes_as_smooth_triangles() -> None:
    soup = preview_scene(_build("#version 2\ntorus\n{ x 2 } ellipsoid\n")).triangles
    assert len(soup) > 100 and set(np.unique(soup.ids)) == {1, 2}


def test_mat_names_are_checked_like_tags() -> None:
    codes = {d.code: d.message for d in analyze("#version 2\n{ mat gold } box\n{ mat nothing } box\n").diagnostics}
    assert "gold" in codes["I203"] and "nothing" in codes["W112"]


def test_v2_defines_and_params_replace_whole_words_only() -> None:
    text = "#version 2\n#define R 3\n#param k float = 0.5 range 0..1\nR * { x 1 s k } R1\nrule R1 { box }\n"
    scene = _build(text)
    assert len(scene) == 3 and abs(float(scene.xform[0, 0, 0]) - 0.5) < 1e-6
    with pytest.raises(Exception, match="Expected"):
        compile_script("#define R 3\nR * { x 1 } R1\nrule R1 { box }\n")  # v1: 'R1' becomes '31'
