"""What a render actually used, for reports (docs/09 §8): the resolved camera and settings, the packed scene,
the acceleration structure, materials and lights. Made once per render job, right after ``prepare``."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..core.scene.camera import Camera
from ..core.scene.material import Material
from .bvh import Bvh
from .config import Frame
from .settings import RenderSettings


@dataclass(frozen=True)
class BvhStats:
    nodes: int
    leaves: int
    depth: int
    mean_leaf_size: float
    max_leaf_size: int
    bytes: int


@dataclass(frozen=True)
class RenderDetails:
    camera: Camera  # the camera the image was rendered with (script, viewport or framed)
    settings: RenderSettings
    prepare_seconds: float
    primitives: int  # packed primitives (instances)
    triangles: int  # explicit triangles (mesh / triangle primitives)
    bvh: BvhStats
    materials: tuple[Material, ...]
    emitters: int  # emissive primitives sampled as lights
    lights: tuple[str, ...]  # declared light types (v2 'light' blocks)
    scene_radius: float


def bvh_stats(bvh: Bvh) -> BvhStats:
    """Node, leaf and depth figures of the flat BVH (inner nodes have their children at a and a + 1)."""
    a, count = bvh.node_u[:, 0].astype(np.int64), bvh.node_u[:, 1].astype(np.int64)
    leaves = count > 0
    depth, frontier = 0, np.zeros(1, np.int64)
    while frontier.size and bvh.nodes:
        inner = frontier[count[frontier] == 0]
        frontier = np.concatenate([a[inner], a[inner] + 1])
        depth += 1
    sizes = count[leaves]
    nbytes = int(bvh.node_f.nbytes + bvh.node_u.nbytes + bvh.order.nbytes)
    mean = float(sizes.mean()) if sizes.size else 0.0
    return BvhStats(bvh.nodes, int(leaves.sum()), depth, mean, int(sizes.max(initial=0)), nbytes)


def render_details(prepared: object, frame: Frame, prepare_seconds: float) -> RenderDetails:
    """``prepared``: a render.api.Prepared (typed loosely to keep this module below render.api)."""
    packed, bvh, table, emitters = (getattr(prepared, n) for n in ("packed", "bvh", "materials", "emitters"))
    lights = tuple(light.type for light in frame.declarations.lights) if frame.declarations else ()
    return RenderDetails(
        camera=frame.camera, settings=frame.settings, prepare_seconds=prepare_seconds,
        primitives=int(packed.prim_u.shape[0]), triangles=int(packed.tri_f.shape[0]), bvh=bvh_stats(bvh),
        materials=tuple(table.materials), emitters=int(emitters.emit_f.shape[0]), lights=lights,
        scene_radius=float(frame.radius),
    )  # fmt: skip
