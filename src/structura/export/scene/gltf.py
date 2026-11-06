"""glTF 2.0 binary (.glb): baked primitives per material with COLOR_0, optionally with boxes and spheres
instanced through EXT_mesh_gpu_instancing (docs/15 §4.2)."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pygltflib as g

from ...core.color import srgb_to_linear
from ...core.geometry.tessellate import TessOptions, TriMesh, tessellate
from ...core.params import ParamSpec, ParamType
from ...core.scene.material import Material
from ..base import Exporter, ExportJob, ExportReport, register
from .gltf_instances import add_instanced_nodes
from .instancing import INSTANCED_KINDS, instance_groups

GLB_LIMIT = 2**31 - 1


class _Blob:
    """Binary buffer builder: appends 4-byte-aligned views and accessors."""

    def __init__(self, doc: g.GLTF2) -> None:
        self.doc, self.data = doc, bytearray()

    def accessor(self, array: np.ndarray, component: int, kind: str, target: int, bounds: bool = False) -> int:
        raw = np.ascontiguousarray(array).tobytes()
        self.data += b"\0" * (-len(self.data) % 4)
        self.doc.bufferViews.append(
            g.BufferView(buffer=0, byteOffset=len(self.data), byteLength=len(raw), target=target)
        )
        self.data += raw
        acc = g.Accessor(bufferView=len(self.doc.bufferViews) - 1, componentType=component, count=len(array), type=kind)
        if bounds:
            acc.min, acc.max = array.min(axis=0).tolist(), array.max(axis=0).tolist()
        self.doc.accessors.append(acc)
        return len(self.doc.accessors) - 1


def _material(m: Material) -> g.Material:
    pbr = g.PbrMetallicRoughness(baseColorFactor=[1, 1, 1, 1], metallicFactor=m.metallic, roughnessFactor=m.roughness)
    mat = g.Material(name=m.name, pbrMetallicRoughness=pbr, doubleSided=True, extensions={})
    if m.transmission > 0:
        mat.extensions["KHR_materials_transmission"] = {"transmissionFactor": m.transmission}
    if m.ior != 1.5:
        mat.extensions["KHR_materials_ior"] = {"ior": m.ior}
    if m.coat > 0:
        mat.extensions["KHR_materials_clearcoat"] = {
            "clearcoatFactor": m.coat,
            "clearcoatRoughnessFactor": m.coat_roughness,
        }
    if m.emission_strength > 0:
        mat.emissiveFactor = [1.0, 1.0, 1.0]
        mat.extensions["KHR_materials_emissive_strength"] = {"emissiveStrength": m.emission_strength}
    return mat


def _camera(job: ExportJob) -> tuple[g.Camera, g.Node]:
    cam = job.model.camera
    forward, right, up = cam.basis
    rot = np.stack([right, up, -forward], axis=1)  # camera looks down −Z
    from ...core.geometry.affine import quaternions  # noqa: PLC0415

    q = quaternions(rot[None])[0]
    perspective = g.Perspective(yfov=math.radians(cam.fov_y_deg), aspectRatio=job.model.aspect, znear=0.01)
    eye = job.model.points(np.asarray(cam.eye, np.float32)[None])[0]
    return g.Camera(type="perspective", perspective=perspective), g.Node(
        name="Camera", camera=0, translation=eye.tolist(), rotation=q.tolist()
    )


def _primitive(blob: _Blob, mesh: TriMesh, job: ExportJob, mask: np.ndarray, material: int) -> g.Primitive:
    tri = mesh.indices[mask]
    used, remap = np.unique(tri, return_inverse=True)
    pos = job.model.points(mesh.positions[used])
    nrm = job.model.directions(mesh.normals[used])
    col = np.hstack([srgb_to_linear(mesh.colors[used, :3]), mesh.colors[used, 3:]]).astype(np.float32)
    attrs = g.Attributes(
        POSITION=blob.accessor(pos, g.FLOAT, "VEC3", g.ARRAY_BUFFER, bounds=True),
        NORMAL=blob.accessor(nrm, g.FLOAT, "VEC3", g.ARRAY_BUFFER),
        COLOR_0=blob.accessor(col, g.FLOAT, "VEC4", g.ARRAY_BUFFER),
    )
    indices = blob.accessor(remap.astype(np.uint32).ravel(), g.UNSIGNED_INT, "SCALAR", g.ELEMENT_ARRAY_BUFFER)
    return g.Primitive(attributes=attrs, indices=indices, material=material)


class _MaterialSlots:
    """Material-table index → glTF material index, appending each material on first use."""

    def __init__(self, doc: g.GLTF2, job: ExportJob) -> None:
        self.doc, self.table, self.slots = doc, job.model.materials, dict[int, int]()

    def __call__(self, index: int) -> int:
        if index not in self.slots:
            self.doc.materials.append(_material(self.table.materials[index]))
            self.slots[index] = len(self.doc.materials) - 1
        return self.slots[index]


class GltfExporter(Exporter):
    name = "gltf"
    title = "glTF 2.0 binary (.glb)"
    extensions: tuple[str, ...] = (".glb",)
    params: tuple[ParamSpec, ...] = (
        ParamSpec("lod", ParamType.ENUM, "medium", "Sphere detail", choices=("low", "medium", "high", "ultra")),
        ParamSpec("unit_scale", ParamType.FLOAT, 1.0, "Unit scale", range=(1e-6, 1e6)),
        ParamSpec("camera", ParamType.BOOL, True, "Include the camera"),
        ParamSpec("instancing", ParamType.BOOL, False, "Instance boxes and spheres (EXT_mesh_gpu_instancing)"),
    )

    def write(self, job: ExportJob, path: Path) -> ExportReport:
        doc = g.GLTF2(asset=g.Asset(generator="Structura"), scenes=[g.Scene(nodes=[])], scene=0)
        blob, slots = _Blob(doc), _MaterialSlots(doc, job)
        counts = {"instanced": 0}
        baked_rows = np.arange(len(job.scene))
        if job.options["instancing"]:
            groups, sheared = instance_groups(job)
            counts["instanced"] = add_instanced_nodes(doc, blob, job, groups, slots)
            baked_rows = np.nonzero(sheared | ~np.isin(job.scene.kind, INSTANCED_KINDS))[0]
        scene = job.scene if len(baked_rows) == len(job.scene) else job.scene.subset(baked_rows)
        mesh = tessellate(scene, TessOptions(lod=job.options["lod"]))
        job.check()
        self._baked(doc, blob, job, mesh, job.model.materials.by_tag[scene.tag[mesh.owners]], slots)
        if job.options["camera"]:
            camera, node = _camera(job)
            doc.cameras.append(camera)
            doc.nodes.append(node)
            doc.scenes[0].nodes.append(len(doc.nodes) - 1)
        self._save(doc, blob, path)
        counts |= {"triangles": mesh.triangles, "materials": len(doc.materials)}
        return ExportReport(path, (path,), counts)

    @staticmethod
    def _baked(doc: g.GLTF2, blob: _Blob, job: ExportJob, mesh: TriMesh, mat_of_tri: np.ndarray, slots: Any) -> None:
        primitives = [
            _primitive(blob, mesh, job, mat_of_tri == index, slots(index))
            for index in range(len(job.model.materials.materials))
            if (mat_of_tri == index).any()
        ]
        if primitives:
            doc.meshes.append(g.Mesh(name="Structura", primitives=primitives))
            doc.nodes.append(g.Node(name="Structura", mesh=len(doc.meshes) - 1))
            doc.scenes[0].nodes.append(len(doc.nodes) - 1)

    @staticmethod
    def _save(doc: g.GLTF2, blob: _Blob, path: Path) -> None:
        if len(blob.data) > GLB_LIMIT:
            raise ValueError("the GLB would exceed 2 GB; export fewer objects or use a lower sphere detail")
        doc.buffers.append(g.Buffer(byteLength=len(blob.data)))
        used = {k for m in doc.materials for k in (m.extensions or {})}
        used |= {k for n in doc.nodes for k in (n.extensions or {})}
        doc.extensionsUsed = sorted(used)
        doc.set_binary_blob(bytes(blob.data))
        doc.save_binary(str(path))


register(GltfExporter())
