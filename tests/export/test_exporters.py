"""Every exporter writes a file its format's reader accepts, with the expected content (docs/15)."""

from __future__ import annotations

import py_compile
import struct
import xml.etree.ElementTree as ET
import zipfile
from functools import cache
from pathlib import Path

import numpy as np
import pygltflib
import pytest
from pxr import Usd, UsdGeom

from structura.core.build.api import build_scene
from structura.core.lang.api import compile_script
from structura.core.scene.ir import SceneIR
from structura.export.api import export_scene
from structura.export.templates.engine import TemplateExport
from structura.export.templates.template_file import bundled_templates, load_template

SCRIPT = """
set background #223
{ x 2 color #f80 } sphere
{ color #4af } box::gold
{ y 2 } grid
{ y -2 s 3 0.1 0.1 } line
{ x -2 } dot
{ s 1 2 1 rz 30 x 3 } box
{ z 2 } triangle[0,0,0;1,0,0;0,1,0]
"""


@cache
def scene() -> SceneIR:
    return build_scene(compile_script(SCRIPT).program).scene


def test_obj_has_vertices_faces_groups_and_materials(tmp_path: Path) -> None:
    report = export_scene(scene(), tmp_path / "s.obj", options={"grouping": "color"})
    text = (tmp_path / "s.obj").read_text()
    faces = sum(line.startswith("f ") for line in text.splitlines())
    assert faces == report.counts["triangles"] > 0
    groups = {line[2:] for line in text.splitlines() if line.startswith("g ")}
    mtl = (tmp_path / "s.mtl").read_text()
    assert all(f"newmtl {g}" in mtl for g in groups)
    assert "cff8800" in groups and len(groups) >= 3  # one group per distinct colour


def test_ply_header_matches_the_payload(tmp_path: Path) -> None:
    export_scene(scene(), tmp_path / "s.ply")
    data = (tmp_path / "s.ply").read_bytes()
    head, _, body = data.partition(b"end_header\n")
    lines = head.decode().splitlines()
    nv = int(next(x for x in lines if x.startswith("element vertex")).split()[-1])
    nf = int(next(x for x in lines if x.startswith("element face")).split()[-1])
    assert len(body) == nv * (24 + 4) + nf * 13


def test_stl_counts_and_watertight_union(tmp_path: Path) -> None:
    report = export_scene(scene(), tmp_path / "s.stl")
    data = (tmp_path / "s.stl").read_bytes()
    (count,) = struct.unpack("<I", data[80:84])
    assert count == report.counts["triangles"] and len(data) == 84 + 50 * count
    two = build_scene(compile_script("box\n{ x 0.5 } box").program).scene
    export_scene(two, tmp_path / "u.stl", options={"watertight": True})
    tris = np.frombuffer((tmp_path / "u.stl").read_bytes()[84:], np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)),
                                                                         ("a", "<u2")]))["v"]  # fmt: skip
    edges = np.sort(np.round(np.stack([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]], 1).reshape(-1, 2, 3), 5), 1)
    _, uses = np.unique(edges.reshape(len(edges), -1), axis=0, return_counts=True)
    assert (uses == 2).all()  # every edge shared by exactly two triangles: a closed manifold


def test_3mf_package_has_model_colours_and_plate(tmp_path: Path) -> None:
    report = export_scene(scene(), tmp_path / "s.3mf")
    with zipfile.ZipFile(tmp_path / "s.3mf") as z:
        assert {"[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"} <= set(z.namelist())
        root = ET.fromstring(z.read("3D/3dmodel.model"))
    ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
    tris = root.findall(".//m:triangle", ns)
    verts = root.findall(".//m:vertex", ns)
    bases = [b.get("displaycolor") for b in root.findall(".//m:base", ns)]
    assert len(tris) == report.counts["triangles"] and len(verts) == report.counts["vertices"]
    assert "#FF8800FF" in bases and max(int(t.get("p1")) for t in tris) < len(bases)
    assert min(float(v.get("z")) for v in verts) == 0.0


def test_x3d_parses_with_coordinates_colours_and_viewpoint(tmp_path: Path) -> None:
    report = export_scene(scene(), tmp_path / "s.x3d")
    root = ET.parse(tmp_path / "s.x3d").getroot()
    its = root.find(".//IndexedTriangleSet")
    assert its is not None
    points = np.array(its.find("Coordinate").get("point").split(), float).reshape(-1, 3)
    colours = np.array(its.find("ColorRGBA").get("color").split(), float).reshape(-1, 4)
    assert len(points) == len(colours) == report.counts["vertices"]
    assert len(its.get("index").split()) == 3 * report.counts["triangles"]
    bg = [float(v) for v in root.find(".//Background").get("skyColor").split()]
    assert bg == pytest.approx([0x22 / 255, 0x22 / 255, 0x33 / 255], abs=1e-5)
    assert float(root.find(".//Viewpoint").get("orientation").split()[-1]) >= 0


def test_vrml_has_matching_points_colours_and_faces(tmp_path: Path) -> None:
    report = export_scene(scene(), tmp_path / "s.wrl")
    text = (tmp_path / "s.wrl").read_text()
    assert text.startswith("#VRML V2.0 utf8") and "Viewpoint {" in text

    def values(node: str) -> list[str]:
        return text.split(node, 1)[1].split("[", 1)[1].split("]", 1)[0].split()

    assert len(values("Coordinate {")) == len(values("Color {")) == 3 * report.counts["vertices"]
    assert values("coordIndex").count("-1") == report.counts["triangles"]


def test_glb_loads_with_vertex_colours_per_material(tmp_path: Path) -> None:
    export_scene(scene(), tmp_path / "s.glb")
    doc = pygltflib.GLTF2().load(str(tmp_path / "s.glb"))
    prims = doc.meshes[0].primitives
    assert len(prims) == len(doc.materials) >= 2
    assert all(p.attributes.COLOR_0 is not None for p in prims)
    assert doc.cameras and doc.asset.generator == "Structura"


def _accessor(doc: pygltflib.GLTF2, index: int, width: int) -> np.ndarray:
    acc = doc.accessors[index]
    view = doc.bufferViews[acc.bufferView]
    raw = doc.binary_blob()[view.byteOffset : view.byteOffset + view.byteLength]
    return np.frombuffer(raw, np.float32).reshape(acc.count, width)


def test_glb_instancing_places_unit_prototypes_like_the_baked_mesh(tmp_path: Path) -> None:
    report = export_scene(scene(), tmp_path / "i.glb", options={"instancing": True})
    doc = pygltflib.GLTF2().load(str(tmp_path / "i.glb"))
    assert "EXT_mesh_gpu_instancing" in doc.extensionsUsed
    nodes = [n for n in doc.nodes if n.extensions and "EXT_mesh_gpu_instancing" in n.extensions]
    attrs = [n.extensions["EXT_mesh_gpu_instancing"]["attributes"] for n in nodes]
    assert (
        sum(doc.accessors[a["TRANSLATION"]].count for a in attrs) == report.counts["instanced"] == 2
    )  # sphere + gold box
    sphere = next(a for n, a in zip(nodes, attrs, strict=True) if n.name.startswith("Sphere"))
    assert _accessor(doc, sphere["TRANSLATION"], 3)[0] == pytest.approx([2.5, 0.5, 0.5], abs=1e-6)
    assert _accessor(doc, sphere["SCALE"], 3)[0] == pytest.approx([0.5] * 3, abs=1e-6)
    colour = _accessor(doc, sphere["_COLOR_0"], 4)[0]
    assert colour[0] == pytest.approx(1.0) and 0 < colour[1] < 0.53  # #f80 in linear light
    assert report.counts["triangles"] > 0  # grid, line, dot, triangle and the sheared box stay baked


@pytest.mark.parametrize("suffix", [".usda", ".usdc", ".usdz"])
def test_usd_instances_bakes_sheared_boxes_and_has_a_camera(tmp_path: Path, suffix: str) -> None:
    path = tmp_path / f"s{suffix}"
    report = export_scene(scene(), path)
    stage = Usd.Stage.Open(str(path))
    instancers = [UsdGeom.PointInstancer(p) for p in stage.Traverse() if p.IsA(UsdGeom.PointInstancer)]
    positions = sum(len(i.GetPositionsAttr().Get()) for i in instancers)
    assert positions == report.counts["instanced"] == 2  # the sphere and the unsheared box
    assert report.counts["baked_rows"] == 1  # 's 1 2 1 rz 30' cannot be TRS
    kinds = {p.GetTypeName() for p in stage.Traverse()}
    assert {"BasisCurves", "Points", "Mesh", "Camera", "Material"} <= kinds
    assert UsdGeom.GetStageUpAxis(stage) == "Y"


def test_blender_script_compiles_and_reads_its_sidecar(tmp_path: Path) -> None:
    report = export_scene(scene(), tmp_path / "s.py")
    py_compile.compile(str(tmp_path / "s.py"), doraise=True)
    data = np.load(tmp_path / "s.npz")
    assert report.counts["materials"] >= 2 and all(k.endswith(("_points", "_faces", "_colors")) for k in data.files)
    assert data[data.files[0]].dtype in (np.float32, np.int32)


def test_template_exporter_matches_the_engine(tmp_path: Path) -> None:
    export_scene(scene(), tmp_path / "s.pov", options={"template": "povray"})
    text = (tmp_path / "s.pov").read_text()
    assert text.count("object {") == TemplateExport(load_template(bundled_templates()["povray"])).render(scene()).count(
        "object {"
    )


def test_unknown_options_and_formats_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown option"):
        export_scene(scene(), tmp_path / "s.obj", options={"colour": True})
    with pytest.raises(ValueError, match="no exporter"):
        export_scene(scene(), tmp_path / "s.xyz")
