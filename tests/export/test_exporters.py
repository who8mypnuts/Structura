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


NS3MF = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}


def _flatten_3mf(path: Path) -> tuple[np.ndarray, int, list[str]]:
    """(world vertices of every placed triangle corner, triangle count, palette) of a 3MF package."""
    with zipfile.ZipFile(path) as z:
        assert {"[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"} <= set(z.namelist())
        root = ET.fromstring(z.read("3D/3dmodel.model"))

    def matrix(text: str | None) -> np.ndarray:
        m = np.array((text or "1 0 0 0 1 0 0 0 1 0 0 0").split(), float).reshape(4, 3)
        return np.hstack([m[:3].T, m[3][:, None]])  # column-vector 3×4

    meshes, corners, count = {}, [], 0
    for obj in root.findall(".//m:object", NS3MF):
        verts = obj.findall("./m:mesh/m:vertices/m:vertex", NS3MF)
        tris = obj.findall("./m:mesh/m:triangles/m:triangle", NS3MF)
        if verts:
            p = np.array([[float(v.get(a)) for a in "xyz"] for v in verts])
            meshes[obj.get("id")] = p[np.array([[int(t.get(k)) for k in ("v1", "v2", "v3")] for t in tris])]
    item = root.find(".//m:build/m:item", NS3MF)
    plate = matrix(item.get("transform"))
    placed = root.findall(f".//m:object[@id='{item.get('objectid')}']/m:components/m:component", NS3MF) or [item]
    for comp in placed:
        m = matrix(comp.get("transform") if comp is not item else None)
        tri = meshes[comp.get("objectid")] @ m[:, :3].T + m[:, 3]
        corners.append(tri @ plate[:, :3].T + plate[:, 3])
        count += len(tri)
    bases = [b.get("displaycolor") for b in root.findall(".//m:base", NS3MF)]
    return np.concatenate(corners).reshape(-1, 3), count, bases


def test_3mf_instanced_and_baked_describe_the_same_solid(tmp_path: Path) -> None:
    baked = export_scene(scene(), tmp_path / "b.3mf", options={"instancing": False})
    instanced = export_scene(scene(), tmp_path / "i.3mf")
    pb, nb, colours = _flatten_3mf(tmp_path / "b.3mf")
    pi, ni, _ = _flatten_3mf(tmp_path / "i.3mf")
    assert nb == ni == baked.counts["triangles"] == instanced.counts["triangles"]
    assert instanced.counts["instances"] == 3 and instanced.counts["prototypes"] == 3  # sphere, 2 box colours
    assert np.allclose(pb.min(axis=0), pi.min(axis=0), atol=1e-3) and np.allclose(
        pb.max(axis=0), pi.max(axis=0), atol=1e-3
    )
    assert pi[:, 2].min() == pytest.approx(0.0, abs=1e-6) and "#FF8800FF" in colours


def test_x3d_parses_with_coordinates_colours_and_viewpoint(tmp_path: Path) -> None:
    report = export_scene(scene(), tmp_path / "s.x3d", options={"instancing": False})
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
    report = export_scene(scene(), tmp_path / "s.wrl", options={"instancing": False})
    text = (tmp_path / "s.wrl").read_text()
    assert text.startswith("#VRML V2.0 utf8") and "Viewpoint {" in text

    def values(node: str) -> list[str]:
        return text.split(node, 1)[1].split("[", 1)[1].split("]", 1)[0].split()

    assert len(values("Coordinate {")) == len(values("Color {")) == 3 * report.counts["vertices"]
    assert values("coordIndex").count("-1") == report.counts["triangles"]


def _axis_angle(values: list[float]) -> np.ndarray:
    x, y, z, a = values
    k = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.eye(3) + np.sin(a) * k + (1 - np.cos(a)) * k @ k


def _x3d_points(root: ET.Element) -> np.ndarray:
    """Every coordinate of an X3D scene graph in world space (Transforms applied, USE resolved)."""
    defs = {g.get("DEF"): g for g in root.iter("IndexedTriangleSet") if g.get("DEF")}
    out = [np.array(g.find("Coordinate").get("point").split(), float).reshape(-1, 3)
           for g in root.iter("IndexedTriangleSet") if g.get("DEF") is None and g.get("USE") is None]  # fmt: skip
    for t in root.iter("Transform"):
        f = {k: [float(v) for v in t.get(k).split()] for k in ("translation", "rotation", "scale", "scaleOrientation")}
        r, so = _axis_angle(f["rotation"]), _axis_angle(f["scaleOrientation"])
        linear = r @ so @ np.diag(f["scale"]) @ so.T
        geometry = t.find(".//IndexedTriangleSet")
        source = defs[geometry.get("USE") or geometry.get("DEF")]
        local = np.array(source.find("Coordinate").get("point").split(), float).reshape(-1, 3)
        out.append(local @ linear.T + np.array(f["translation"]))
    return np.concatenate(out)


def test_x3d_and_vrml_instances_reproduce_the_baked_geometry(tmp_path: Path) -> None:
    export_scene(scene(), tmp_path / "b.x3d", options={"instancing": False})
    report = export_scene(scene(), tmp_path / "i.x3d")
    baked = _x3d_points(ET.parse(tmp_path / "b.x3d").getroot())
    placed = _x3d_points(ET.parse(tmp_path / "i.x3d").getroot())
    assert report.counts["instances"] == 3  # the sphere and both boxes (one sheared)
    assert np.allclose(baked.min(axis=0), placed.min(axis=0), atol=1e-4)
    assert np.allclose(baked.max(axis=0), placed.max(axis=0), atol=1e-4)
    export_scene(scene(), tmp_path / "i.wrl")
    text = (tmp_path / "i.wrl").read_text()
    assert text.count("Transform {") == 3 and text.count("DEF box") == 1 and text.count("USE box") == 1


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
    assert report.counts["baked_rows"] == 3  # the grid, the triangle and 's 1 2 1 rz 30' (not a TRS)
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
    export_scene(scene(), tmp_path / "s.pov", name="template", options={"template": "povray"})
    text = (tmp_path / "s.pov").read_text()
    assert text.count("object {") == TemplateExport(load_template(bundled_templates()["povray"])).render(scene()).count(
        "object {"
    )


def test_unknown_options_and_formats_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown option"):
        export_scene(scene(), tmp_path / "s.obj", options={"colour": True})
    with pytest.raises(ValueError, match="no exporter"):
        export_scene(scene(), tmp_path / "s.xyz")


def _world_points(stage: Usd.Stage) -> np.ndarray:
    """Every mesh point in world space (instance proxies included)."""
    cache = UsdGeom.XformCache()
    out = []
    for prim in stage.Traverse(Usd.TraverseInstanceProxies()):
        if prim.IsA(UsdGeom.Mesh) and not str(prim.GetPath()).startswith("/StructuraPrototypes"):
            pts = np.array(UsdGeom.Mesh(prim).GetPointsAttr().Get(), float)
            m = np.array(cache.GetLocalToWorldTransform(prim), float)
            out.append(pts @ m[:3, :3] + m[3, :3])
    return np.concatenate(out)


def test_usd_matrix_policy_places_sheared_and_v2_solids_exactly(tmp_path: Path) -> None:
    text = "#version 2\n" + SCRIPT + "{ x 5 } ellipsoid\n{ x 6 } cone[0.5]\n"
    v2 = build_scene(compile_script(text).program).scene
    baked = export_scene(v2, tmp_path / "b.usda")
    matrix = export_scene(v2, tmp_path / "m.usda", options={"shear": "matrix"})
    assert matrix.counts["matrix_instances"] == 3 and baked.counts["baked_rows"] == matrix.counts["baked_rows"] + 3
    stage_b, stage_m = Usd.Stage.Open(str(tmp_path / "b.usda")), Usd.Stage.Open(str(tmp_path / "m.usda"))
    pb = _world_points(stage_b)
    pm = _world_points(stage_m)
    assert np.allclose(pb.max(axis=0), pm.max(axis=0), atol=1e-4) and np.allclose(
        pb.min(axis=0), pm.min(axis=0), atol=1e-4
    )
    flat = export_scene(v2, tmp_path / "f.usda", options={"mode": "flattened"})
    stage_f = Usd.Stage.Open(str(tmp_path / "f.usda"))
    assert flat.counts["instanced"] == 0 and not any(p.IsA(UsdGeom.PointInstancer) for p in stage_f.Traverse())


def _balanced(text: str) -> bool:
    depth = 0
    for char in text:
        depth += {"{": 1, "}": -1}.get(char, 0)
        if depth < 0:
            return False
    return depth == 0


V2_SCENE = "#version 2\n" + SCRIPT + "{ x 5 } cone[0.5]\n{ x 6 } torus[0.3]::glass\n{ x 7 } ellipsoid\n"


def test_povray_and_sunflow_scenes_place_every_solid_with_a_matrix(tmp_path: Path) -> None:
    v2 = build_scene(compile_script(V2_SCENE).program).scene
    pov = export_scene(v2, tmp_path / "s.pov")
    text = (tmp_path / "s.pov").read_text()
    assert pov.counts["instances"] == 6 and text.count("matrix <") == 6 and _balanced(text)
    assert "#version 3.8;" in text and "mesh2 {" in text and "interior { ior 1.5 }" in text
    export_scene(v2, tmp_path / "s.sc")
    sc = (tmp_path / "s.sc").read_text()
    assert sc.count("instance {") == 6 and sc.count("transform row") == 6 and _balanced(sc)
    assert sc.count("noinstance") == 5 and "face_shaders" in sc  # box, sphere, cone, torus, ellipsoid


def test_mitsuba_scene_references_its_meshes_and_bsdfs(tmp_path: Path) -> None:
    v2 = build_scene(compile_script(V2_SCENE).program).scene
    report = export_scene(v2, tmp_path / "s.xml")
    root = ET.parse(tmp_path / "s.xml").getroot()
    ids = {e.get("id") for e in root.iter() if e.get("id")}
    refs = {r.get("id") for r in root.iter("ref")}
    assert refs <= ids and len(root.findall("shape[@type='instance']")) == report.counts["instances"] == 6
    for name in root.iter("string"):
        if name.get("name") == "filename":
            assert (tmp_path / name.get("value")).stat().st_size > 0


def test_blender_instanced_mode_writes_point_clouds_for_geometry_nodes(tmp_path: Path) -> None:
    v2 = build_scene(compile_script(V2_SCENE).program).scene
    report = export_scene(v2, tmp_path / "s.py", options={"geometry": "instanced"})
    py_compile.compile(str(tmp_path / "s.py"), doraise=True)
    data = np.load(tmp_path / "s.npz")
    clouds = [k.removesuffix("_location") for k in data.files if k.endswith("_location")]
    assert report.counts["instanced"] == sum(len(data[f"{c}_location"]) for c in clouds) == 5  # not the sheared box
    for c in clouds:
        n = len(data[f"{c}_location"])
        assert data[f"{c}_rotation"].shape == (n, 4) and data[f"{c}_scale"].shape == (n, 3)
        assert np.allclose(np.linalg.norm(data[f"{c}_rotation"], axis=1), 1.0, atol=1e-5)
    text = (tmp_path / "s.py").read_text()
    assert "GeometryNodeInstanceOnPoints" in text and '"instanced": [' in text
