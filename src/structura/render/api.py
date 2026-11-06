"""Render entry points shared by the GUI services and the CLI (docs/09 §3)."""

from __future__ import annotations

import time
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from functools import cache
from typing import Any

import numpy as np

from ..compute.base import Backend, Launch
from ..core.scene.declarations import SceneDeclarations
from ..core.scene.ir import SceneIR
from ..core.scene.material import Material
from ..core.scene.material_library import MaterialTable, resolve_materials
from ..core.scene.settings import SceneSettings, settings_from_events
from ..kernels.skl import ir
from ..kernels.skl.frontend import compile_module
from .bvh import Bvh, build_bvh
from .config import Frame, config, scene_frame
from .declarations import declared_settings
from .kernels.passes import render_pass
from .legacy import with_legacy
from .lights import pack_lights
from .materials import pack_materials
from .pack import PackedScene, PackOptions, pack_scene
from .settings import INTEGRATORS, RenderSettings


@cache
def render_module() -> ir.Module:
    return compile_module([render_pass])


@dataclass(frozen=True)
class Prepared:
    """Everything a backend needs, reusable across passes and camera changes."""

    packed: PackedScene
    bvh: Bvh
    materials: MaterialTable
    scene_settings: SceneSettings
    declarations: SceneDeclarations | None
    lo: np.ndarray
    hi: np.ndarray


@dataclass(frozen=True)
class RenderProgress:
    image: np.ndarray  # float32[H, W, 3] linear radiance estimate
    samples: int
    seconds: float


def prepare(scene: SceneIR, declared: Mapping[str, Material] | None = None, tag_presets: bool = False) -> Prepared:
    """Pack, build the BVH and resolve materials (declared ones, then presets named like a tag if enabled).

    v2 scripts bring their own 'material' blocks and always enable tag presets (docs/05 §9.3).
    """
    if scene.declarations is not None:
        declared, tag_presets = {**scene.declarations.materials, **(declared or {})}, True
    scene_settings = settings_from_events(scene.events)
    materials = resolve_materials(scene.tags, scene_settings.raytracer, declared, tag_presets)
    packed = pack_scene(scene, PackOptions(material_of_tag=materials.by_tag))
    bvh = build_bvh(packed.lo, packed.hi)
    if len(packed):
        lo, hi = packed.lo.min(axis=0), packed.hi.max(axis=0)
    else:
        lo, hi = np.full(3, -1.0, np.float32), np.full(3, 1.0, np.float32)
    return Prepared(packed, bvh, materials, scene_settings, scene.declarations, lo, hi)


def script_settings(scene: SceneIR, base: RenderSettings | None = None) -> RenderSettings:
    """``base`` (or the defaults) updated with the script's 'set raytracer::…' values and v2 blocks."""
    settings = with_legacy(base or RenderSettings(), settings_from_events(scene.events).raytracer)
    has_background = any(event.key == "background" for event, _, _ in scene.events)
    return declared_settings(settings, scene.declarations, has_background)


def _nonempty(a: np.ndarray, dtype: type[np.generic]) -> np.ndarray:
    flat = np.ascontiguousarray(a, dtype=dtype).ravel()
    return flat if flat.size else np.zeros(1, dtype)


def launch_args(prepared: Prepared, frame: Frame) -> dict[str, Any]:
    st, p, b = frame.settings, prepared.packed, prepared.bvh
    return {
        "width": st.width,
        "height": st.height,
        "integrator": INTEGRATORS[st.integrator],
        "max_bounces": st.max_bounces,
        "ao_samples": st.ao_samples,
        "cfg": config(frame),
        "prim_f": _nonempty(p.prim_f, np.float32),
        "prim_u": _nonempty(p.prim_u, np.uint32),
        "tri_f": _nonempty(p.tri_f, np.float32),
        "node_f": _nonempty(b.node_f, np.float32),
        "node_u": _nonempty(b.node_u, np.uint32),
        "order": _nonempty(b.order, np.uint32),
        "mat_f": _nonempty(pack_materials(prepared.materials), np.float32),
        "light_f": _nonempty(pack_lights(prepared.declarations), np.float32),
        "accum": np.zeros(st.width * st.height * 4, np.float32),
        "sample_base": 0,
        "spp": 0,
    }


def progressive(
    scene: SceneIR | Prepared, settings: RenderSettings, backend: Backend, frame: Frame | None = None
) -> Iterator[RenderProgress]:
    """Yield an updated image after every pass of settings.samples_per_pass samples."""
    started = time.perf_counter()
    prepared = scene if isinstance(scene, Prepared) else prepare(scene)
    frame = frame or scene_frame(prepared.scene_settings, settings, prepared.lo, prepared.hi, prepared.declarations)
    w, h = settings.width, settings.height
    launch = Launch(render_module(), "render_pass", (w, h, 1), launch_args(prepared, frame))
    bound = backend.bind(launch)
    done = 0
    while done < settings.samples:
        spp = min(settings.samples_per_pass, settings.samples - done)
        bound.update(sample_base=settings.seed * 1_000_003 + done, spp=spp)
        bound.dispatch()
        done += spp
        accum = bound.read("accum").reshape(h, w, 4)
        yield RenderProgress(accum[..., :3] / np.maximum(accum[..., 3:], 1.0), done, time.perf_counter() - started)


def render(
    scene: SceneIR | Prepared, settings: RenderSettings, backend: Backend, frame: Frame | None = None
) -> RenderProgress:
    *_, last = progressive(scene, settings, backend, frame)
    return last
