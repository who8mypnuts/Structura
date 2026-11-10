"""What a render actually used, for reports (docs/09 §8): the resolved camera and settings, the packed scene,
the acceleration structure, materials and lights. Made once per render job, right after ``prepare``."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..core.lang.v2.block_form import value_text
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
    """What a render used, for reports (everything resolved: no defaults left to guess).

    Attributes:
        camera: The camera the image was rendered with (script, viewport or framed).
        settings: The render settings.
        prepare_seconds: Time to pack the scene and build the BVH.
        primitives: Packed primitives (instances).
        triangles: Explicit triangles (mesh and triangle primitives).
        bvh: BVH figures.
        materials: The material table.
        emitters: Emissive primitives sampled as lights.
        lights: Declared light types (v2 'light' blocks).
        scene_radius: Half the diagonal of the structure's bounding box.
        device: What the backend says about its device (name → value: driver, memory …).
        light_specs: (name, type, values as the script writes them) of every declared light.
    """

    camera: Camera
    settings: RenderSettings
    prepare_seconds: float
    primitives: int
    triangles: int
    bvh: BvhStats
    materials: tuple[Material, ...]
    emitters: int
    lights: tuple[str, ...]
    scene_radius: float
    device: tuple[tuple[str, str], ...] = ()
    light_specs: tuple[tuple[str, str, str], ...] = ()


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


def _light_text(values: dict[str, object]) -> str:
    """A light's values as its block writes them ('position [0 5 0]  power 200')."""
    return "  ".join(f"{key} {value_text(value)}" for key, value in values.items())


def render_details(
    prepared: object, frame: Frame, prepare_seconds: float, device: dict[str, str] | None = None
) -> RenderDetails:
    """Collects what a render used.

    Args:
        prepared: A render.api.Prepared (typed loosely so this module stays below render.api).
        frame: The view and settings.
        prepare_seconds: Time spent preparing.
        device: The backend's ``details()``.

    Returns:
        The details.
    """
    packed, bvh, table, emitters = (getattr(prepared, n) for n in ("packed", "bvh", "materials", "emitters"))
    declared = frame.declarations.lights if frame.declarations else ()
    lights = tuple(light.type for light in declared)
    return RenderDetails(
        camera=frame.camera, settings=frame.settings, prepare_seconds=prepare_seconds,
        primitives=int(packed.prim_u.shape[0]), triangles=int(packed.tri_f.shape[0]), bvh=bvh_stats(bvh),
        materials=tuple(table.materials), emitters=int(emitters.emit_f.shape[0]), lights=lights,
        scene_radius=float(frame.radius), device=tuple((device or {}).items()),
        light_specs=tuple((light.name, light.type, _light_text(light.values)) for light in declared),
    )  # fmt: skip
