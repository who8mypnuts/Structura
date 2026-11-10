"""PyMeshLab in the export pipeline (PLAN Q4): clean-ups, mesh checks and MeshLab projects."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

from structura.cli.main import main
from structura.core.build.api import build_scene
from structura.core.geometry.tessellate import tessellate
from structura.core.geometry.trimesh import TriMesh
from structura.core.lang.api import compile_script
from structura.core.scene.ir import SceneIR
from structura.export.api import export_scene
from structura.export.mesh.meshlab import check_mesh, clean_up, from_meshset, to_meshset


def _scene(text: str) -> SceneIR:
    return build_scene(compile_script(text).program).scene


def test_a_mesh_round_trips_with_colours_and_owners() -> None:
    mesh = tessellate(_scene("{ color #f00 } box\n{ x 2 color #00f } sphere\n"))
    _, ms = to_meshset(mesh)
    back = from_meshset(ms)
    assert back.triangles == mesh.triangles and len(back.positions) == len(mesh.positions)
    assert set(np.unique(back.owners).tolist()) == {0, 1}
    assert np.allclose(back.colors[back.indices[back.owners == 1][0, 0], :3], (0.0, 0.0, 1.0))


def test_welding_makes_a_box_watertight_and_checks_say_so() -> None:
    box = tessellate(_scene("box\n"))
    assert check_mesh(box).watertight and check_mesh(box).volume == pytest.approx(1.0, rel=1e-3)
    assert not check_mesh(box, weld=False).watertight  # the unit box is stored with split normals
    welded = clean_up(box, "clean")
    assert len(welded.positions) == 8 and welded.triangles == 12


def test_print_ready_closes_holes() -> None:
    box = clean_up(tessellate(_scene("box\n")), "clean")
    open_box = box.select(np.arange(box.triangles) >= 2)  # one face (two triangles) removed
    assert not check_mesh(open_box).watertight and check_mesh(open_box).holes == 1
    assert check_mesh(clean_up(open_box, "print-ready")).watertight


def test_light_decimates_to_the_share_kept() -> None:
    sphere = tessellate(_scene("sphere\n"))
    light = clean_up(sphere, "light", keep=0.5)
    assert 0.4 * sphere.triangles < light.triangles < 0.6 * sphere.triangles


def test_clean_up_keeps_grouping_by_tag(tmp_path: Path) -> None:
    scene = _scene("box::gold\n{ x 2 } sphere::glass\n")
    export_scene(scene, tmp_path / "s.obj", options={"cleanup": "clean", "grouping": "tag"})
    groups = {line[2:] for line in (tmp_path / "s.obj").read_text().splitlines() if line.startswith("g ")}
    assert groups == {"gold", "glass"}


def test_a_meshlab_project_has_one_layer_per_material(tmp_path: Path) -> None:
    scene = _scene("#version 2\nmaterial a { preset gold }\nbox::a\n{ x 2 } sphere::b\n{ x 4 } box::a\n")
    report = export_scene(scene, tmp_path / "scene.mlp")
    root = ET.fromstring((tmp_path / "scene.mlp").read_text().split("\n", 1)[1])
    layers = root.findall("MeshGroup/MLMesh")
    assert sorted(m.get("label") for m in layers) == ["a", "b"] and report.counts["layers"] == 2
    for mesh in layers:
        ply = tmp_path / str(mesh.get("filename"))
        assert ply.read_bytes().startswith(b"ply\n") and "1 0 0 0" in str(mesh.findtext("MLMatrix44"))


def test_the_command_line_takes_the_clean_up(tmp_path: Path) -> None:
    script = tmp_path / "s.es"
    script.write_text("3 * { x 0.5 } box\n")
    assert main(["export", str(script), "-o", str(tmp_path / "s.stl"), "--option", "cleanup=print-ready"]) == 0
    assert (tmp_path / "s.stl").stat().st_size > 84


def test_the_select_helper_keeps_only_used_vertices() -> None:
    mesh = TriMesh(np.eye(4, 3, dtype=np.float32), np.zeros((4, 3), np.float32), np.ones((4, 4), np.float32),
                   np.array([[0, 1, 2], [1, 2, 3]], np.uint32), np.array([5, 6]))  # fmt: skip
    part = mesh.select(np.array([False, True]))
    assert len(part.positions) == 3 and part.indices.tolist() == [[0, 1, 2]] and part.owners.tolist() == [6]


def test_a_missing_pymeshlab_is_explained(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins  # noqa: PLC0415

    from structura.export.mesh import meshlab  # noqa: PLC0415

    real_import = builtins.__import__

    def no_meshlab(name: str, *args: object, **kwargs: object) -> object:
        if name == "pymeshlab":
            raise ImportError("libOpenGL.so.0: cannot open shared object file")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", no_meshlab)
    with pytest.raises(meshlab.MeshLabUnavailableError, match="libopengl0"):
        meshlab._pymeshlab()
