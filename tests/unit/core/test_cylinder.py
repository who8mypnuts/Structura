"""Cylinders in every dialect and every consumer (PLAN Q9): Structure Synth 1.5 counted `cylinder` but drew
nothing; Structura draws it in v1 and v2, while the 1.5 template and OBJ layouts stay byte-identical."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from structura.compute.cpu import CpuBackend
from structura.core.build.api import build_scene
from structura.core.geometry.tessellate import tessellate
from structura.core.lang.analysis import analyze
from structura.core.lang.api import compile_script
from structura.core.lang.assist import complete
from structura.core.lang.diagnostics import Severity
from structura.core.lang.fixes import apply_edits, quick_fixes
from structura.core.scene.ir import PrimitiveKind as K
from structura.core.scene.ir import SceneIR
from structura.export.api import export_scene
from structura.export.legacy_obj import LegacyObjExport
from structura.export.templates.engine import TemplateExport
from structura.export.templates.template_file import LegacyTemplate, bundled_templates, load_template
from structura.preview.instances import preview_scene
from structura.render.api import prepare_with_frame, render
from structura.render.settings import RenderSettings

V1 = "{ s 2 1 1 } cylinder\n{ y 2 } box\n"
V2 = "#version 2\n" + V1


def _scene(text: str) -> SceneIR:
    return build_scene(compile_script(text).program).scene


@pytest.mark.parametrize("text", [V1, V2], ids=["v1", "v2"])
def test_cylinders_build_and_tessellate_in_both_dialects(text: str) -> None:
    scene = _scene(text)
    assert [K(k) for k in scene.kind] == [K.CYLINDER, K.BOX]
    mesh = tessellate(scene)
    assert set(np.unique(mesh.owners).tolist()) == {0, 1}
    assert 0 in preview_scene(scene).triangles.ids - 1  # the GL preview draws it (smooth triangle soup)


def test_v1_cylinders_render_in_the_precision_engine() -> None:
    settings = RenderSettings(width=48, height=32, samples=1, samples_per_pass=1, integrator="preview", aovs=True,
                              frame=True)  # fmt: skip
    prepared, frame = prepare_with_frame(_scene("cylinder\n"), settings)
    aovs = render(prepared, settings, CpuBackend(), frame).aovs
    assert aovs is not None and aovs.alpha.mean() > 0.05


@pytest.mark.parametrize("suffix", [".obj", ".ply", ".stl", ".3mf", ".glb", ".usda", ".x3d", ".wrl"])
def test_every_mesh_and_scene_format_exports_v1_cylinders(tmp_path: Path, suffix: str) -> None:
    report = export_scene(_scene(V1), tmp_path / f"c{suffix}")
    assert report.path.stat().st_size > 200


def test_a_watertight_stl_includes_the_cylinder(tmp_path: Path) -> None:
    report = export_scene(_scene("cylinder\n"), tmp_path / "c.stl", options={"watertight": True})
    assert report.path.stat().st_size > 84 + 50 * 50


def _template() -> TemplateExport:
    return TemplateExport(load_template(bundled_templates()["Sunflow-Colored"]))


def test_1_5_templates_and_obj_still_omit_v1_cylinders() -> None:
    with_cylinder, without = _scene(V1), _scene("{ y 2 } box\n")
    assert _template().render(with_cylinder) == _template().render(without)  # byte-identical to 1.5
    assert LegacyObjExport().render(with_cylinder) == LegacyObjExport().render(without)


def test_templates_accept_v2_solids_and_say_which_they_lack() -> None:
    export = _template()
    text = export.render(_scene("#version 2\ncylinder\ncone[0.5]\ntorus\nbox\n"))  # used to raise KeyError
    assert "box" in " ".join(load_template(bundled_templates()["Sunflow-Colored"]).primitives)
    assert any("'cylinder'" in w for w in export.warnings) and any("'torus'" in w for w in export.warnings)
    assert text


def test_a_template_with_a_cylinder_section_gets_the_box_placeholders() -> None:
    sections = {"begin": "", "end": "", "cylinder": "C {matrix} {param} {r}\n", "cone": "K {param}\n"}
    template = LegacyTemplate("t", primitives=sections)
    text = TemplateExport(template).render(_scene("#version 2\ncylinder\ncone[0.5]\n"))
    assert text.startswith("C 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 ") and "K 0.5" in text


def test_w105_is_now_information() -> None:
    found = [d for d in analyze("cylinder\n").diagnostics if d.code == "W105"]
    assert found and found[0].severity == Severity.INFO and "Structura does" in found[0].message


def _fixed(text: str, code: str) -> str:
    found = [d for d in analyze(text).diagnostics if d.code == code]
    assert found, f"no {code} in {[d.code for d in analyze(text).diagnostics]}"
    fixes = quick_fixes(text, found)
    assert fixes
    return apply_edits(text, fixes[0].edits)


def test_a_v2_primitive_in_a_v1_script_says_what_it_needs() -> None:
    text = "cone[0.5]\ntorus::gold\n"
    error = next(d for d in analyze(text).diagnostics if d.code == "E018")
    assert "'cone' is an EisenScript v2 primitive" in error.message
    fixed = _fixed(text, "E018")
    assert fixed.startswith("#version 2\n") and analyze(fixed).ok


def test_a_misplaced_version_line_is_reported_and_moved() -> None:
    text = "// my script\n#version 2\ncone\n"
    fixed = _fixed(text, "W116")
    assert fixed == "#version 2\n// my script\ncone\n" and analyze(fixed).ok
    assert not [d for d in analyze("#version 2\ncone\n").diagnostics if d.code == "W116"]


def test_completion_marks_v2_only_primitives_in_v1_scripts() -> None:
    v1 = {i.label: i.detail for i in complete("co", 2).items}
    v2 = {i.label: i.detail for i in complete("#version 2\nco", 13).items}
    assert "needs '#version 2'" in v1["cone"] and "needs" not in v2["cone"]
    assert "needs" not in {i.label: i.detail for i in complete("cy", 2).items}["cylinder"]
