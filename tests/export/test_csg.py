"""CSG markers evaluated with manifold3d (docs/15 §3.1)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from structura.core.build.api import build_scene
from structura.core.lang.api import compile_script
from structura.core.text_file import read_script
from structura.export.api import export_scene
from structura.export.csg import Group, csg_mesh, csg_tree

BOXES = (
    "set recursion depth\ntemplate::{op}-begin\n{{ s 2 }} box\n{{ x 1 s 2 }} box\ntemplate::{op}-end\n{{ x 5 }} box\n"
)


def _volume(corners: np.ndarray) -> float:
    return float(np.einsum("ti,ti->t", corners[:, 0], np.cross(corners[:, 1], corners[:, 2])).sum() / 6)


def _mesh_volume(text: str) -> float:
    mesh, warnings = csg_mesh(build_scene(compile_script(text).program).scene)
    assert not warnings
    return _volume(mesh.positions[mesh.indices].astype(np.float64))


@pytest.mark.parametrize(("op", "volume"), [("union", 12.0), ("difference", 4.0), ("intersection", 4.0)])
def test_box_booleans(op: str, volume: float) -> None:
    assert _mesh_volume(BOXES.format(op=op)) == pytest.approx(volume + 1.0, rel=1e-4)  # + the loose unit box


def test_the_tree_follows_emission_order_and_reports_unbalanced_markers() -> None:
    text = "set recursion depth\ntemplate::union-begin\nbox\ntemplate::difference-begin\nbox\nsphere\n" \
           "template::difference-end\ntemplate::union-end\ntemplate::union-begin\nbox\n"  # fmt: skip
    root, warnings = csg_tree(build_scene(compile_script(text).program).scene)
    first = root.items[0]
    assert isinstance(first, Group) and first.op == "union" and isinstance(first.items[1], Group)
    assert first.items[1].op == "difference" and len(first.items[1].items) == 2
    assert warnings and "never closed" in warnings[0]


def test_the_legacy_csg_example_prints_as_one_solid(tmp_path: Path) -> None:
    example = Path(__file__).parents[2] / "src/structura/resources/legacy/examples/Tutorials/CSG test.es"
    text = read_script(example).replace("set maxdepth 17", "set maxdepth 4").replace("md 17", "md 4")
    scene = build_scene(compile_script(text).program).scene
    plain = export_scene(scene, tmp_path / "plain.stl")
    solid = export_scene(scene, tmp_path / "csg.stl", options={"csg": True})
    assert solid.counts["triangles"] > 0 and solid.counts["triangles"] != plain.counts["triangles"]
    data = (tmp_path / "csg.stl").read_bytes()
    tris = np.frombuffer(data[84:], np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))["v"]
    assert _volume(tris.astype(np.float64)) > 0  # a closed, outward-facing solid
