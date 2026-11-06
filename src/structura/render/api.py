"""Render entry points shared by the GUI services and the CLI (docs/09 §3)."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, replace
from functools import cache
from typing import Any

import numpy as np

from ..compute.base import Backend, Launch
from ..core.scene.camera import Camera
from ..core.scene.declarations import SceneDeclarations
from ..core.scene.ir import SceneIR
from ..core.scene.material import Material
from ..core.scene.material_library import MaterialTable, resolve_materials
from ..core.scene.settings import SceneSettings, settings_from_events
from ..kernels.skl import ir
from ..kernels.skl.frontend import compile_module
from .aovs import Aovs, render_aovs
from .bands import Bands
from .bvh import Bvh, build_bvh
from .config import Frame, config, scene_frame
from .declarations import declared_settings
from .emitters import Emitters, pack_emitters
from .environment import settings_environment
from .film import active_mask, film_image, initial_mask, new_film
from .ground import Ground, with_ground
from .kernels.layout import N_EMITTERS
from .kernels.passes import render_pass
from .legacy import with_legacy
from .lights import pack_lights
from .materials import pack_materials
from .pacing import Pacing
from .pack import PackedScene, PackOptions, pack_scene
from .photons import add_photons
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
    emitters: Emitters
    scene_settings: SceneSettings
    declarations: SceneDeclarations | None
    lo: np.ndarray
    hi: np.ndarray


@dataclass(frozen=True)
class RenderProgress:
    image: np.ndarray  # float32[H, W, 3] linear radiance estimate
    samples: int  # the most samples any pixel has
    seconds: float
    aovs: Aovs | None = None  # when settings.aovs
    sample_map: np.ndarray | None = None  # int32[H, W] samples per pixel (adaptive sampling varies them)
    active: float = 1.0  # the fraction of pixels still being sampled


def prepare(
    scene: SceneIR, declared: Mapping[str, Material] | None = None, tag_presets: bool = False,
    ground: Ground | None = None,
) -> Prepared:  # fmt: skip
    """Pack, build the BVH and resolve materials (declared ones, then presets named like a tag if enabled).

    v2 scripts bring their own 'material' blocks and always enable tag presets (docs/05 §9.3). ``ground``
    adds a ground plane or shadow catcher under the scene (excluded from the framing bounds).
    """
    if scene.declarations is not None:
        declared, tag_presets = {**scene.declarations.materials, **(declared or {})}, True
    scene_settings = settings_from_events(scene.events)
    materials = resolve_materials(scene.tags, scene_settings.raytracer, declared, tag_presets)
    packed = pack_scene(scene, PackOptions(material_of_tag=materials.by_tag))
    if len(packed):
        lo, hi = packed.lo.min(axis=0), packed.hi.max(axis=0)
    else:
        lo, hi = np.full(3, -1.0, np.float32), np.full(3, 1.0, np.float32)
    if ground is not None:
        packed, materials = with_ground(packed, materials, ground, len(scene), lo, hi)
    bvh = build_bvh(packed.lo, packed.hi)
    emitters = pack_emitters(packed, pack_materials(materials), scene.xform)
    return Prepared(packed, bvh, materials, emitters, scene_settings, scene.declarations, lo, hi)


def prepare_with_frame(
    scene: SceneIR, settings: RenderSettings, tag_presets: bool = False, camera: Camera | None = None
) -> tuple[Prepared, Frame]:
    """``prepare`` (with the settings' ground) and the view: ``camera``, else the script camera or framing."""
    prepared = prepare(scene, tag_presets=tag_presets, ground=settings.ground_spec)
    frame = scene_frame(prepared.scene_settings, settings, prepared.lo, prepared.hi, prepared.declarations)
    return prepared, frame if camera is None else replace(frame, camera=camera)


def script_settings(scene: SceneIR, base: RenderSettings | None = None) -> RenderSettings:
    """``base`` (or the defaults) updated with the script's 'set raytracer::…' values and v2 blocks."""
    settings = with_legacy(base or RenderSettings(), settings_from_events(scene.events).raytracer)
    has_background = any(event.key == "background" for event, _, _ in scene.events)
    return declared_settings(settings, scene.declarations, has_background)


def _nonempty(a: np.ndarray, dtype: type[np.generic]) -> np.ndarray:
    flat = np.ascontiguousarray(a, dtype=dtype).ravel()
    return flat if flat.size else np.zeros(1, dtype)


def _joined(data: np.ndarray, cdf: np.ndarray) -> np.ndarray:
    """A record buffer with its sampling CDF appended (the kernels find the CDF after the records)."""
    return _nonempty(np.concatenate([np.ravel(data), np.ravel(cdf)]), np.float32)


def launch_args(prepared: Prepared, frame: Frame) -> dict[str, Any]:
    st, p, b = frame.settings, prepared.packed, prepared.bvh
    env = settings_environment(st)
    cfg = config(frame)
    cfg[N_EMITTERS] = len(prepared.emitters)  # the count lives with the scene, the rest of cfg with the frame
    return {
        "width": st.width,
        "height": st.height,
        "integrator": INTEGRATORS[st.integrator],
        "max_bounces": st.max_bounces,
        "ao_samples": st.ao_samples,
        "cfg": cfg,
        "prim_f": _nonempty(p.prim_f, np.float32),
        "prim_u": _nonempty(p.prim_u, np.uint32),
        "tri_f": _nonempty(p.tri_f, np.float32),
        "node_f": _nonempty(b.node_f, np.float32),
        "node_u": _nonempty(b.node_u, np.uint32),
        "order": _nonempty(b.order, np.uint32),
        "mat_f": _nonempty(pack_materials(prepared.materials), np.float32),
        "light_f": _nonempty(pack_lights(prepared.declarations), np.float32),
        "env_f": _joined(env.rgb, env.cdf) if env else np.zeros(3, np.float32),
        "emit_f": _joined(prepared.emitters.emit_f, prepared.emitters.emit_cdf),
        "prim_emit": _nonempty(prepared.emitters.prim_emit, np.uint32),
        "photon_f": np.zeros(1, np.float32),
        "pixel_mask": initial_mask(st.width, st.height, st.region),
        "accum": new_film(st.width, st.height),
        "row0": 0,
        "sample_base": 0,
        "spp": 0,
    }


def progressive(
    scene: SceneIR | Prepared,
    settings: RenderSettings,
    backend: Backend,
    frame: Frame | None = None,
    between: Callable[[], None] | None = None,
) -> Iterator[RenderProgress]:
    """Yield an updated image after every pass (render/pacing.py sizes the passes).

    Stops at settings.samples, at the time limit, or when adaptive sampling finds every pixel below the
    noise threshold. ``between`` runs between the row bands of each pass (cancellation checks).
    """
    started = time.perf_counter()
    prepared = scene if isinstance(scene, Prepared) else prepare(scene)
    frame = frame or scene_frame(prepared.scene_settings, settings, prepared.lo, prepared.hi, prepared.declarations)
    w, h = settings.width, settings.height
    args = launch_args(prepared, frame)
    if settings.caustics == "photons":
        add_photons(args, prepared.lo, prepared.hi, settings.photon_count, settings.photon_radius, backend,
                    settings.seed)  # fmt: skip
    aovs = render_aovs(args, backend) if settings.aovs else None
    bound = backend.bind(Launch(render_module(), "render_pass", (w, h, 1), args))
    bands, counts, active = Bands(w, h), np.zeros((h, w), np.int32), args["pixel_mask"]
    done, pacing = 0, Pacing(settings)
    while done < settings.samples and active.any():
        spp = pacing.next(done)
        bound.update(sample_base=settings.seed * 1_000_003 + done, spp=spp)
        pacing.observe(spp, bands.dispatch(bound, between))
        done += spp
        counts += active.reshape(h, w).astype(np.int32) * spp
        accum = bound.read("accum")
        seconds = time.perf_counter() - started
        if settings.noise_threshold > 0 and done >= settings.adaptive_min_samples:
            active = active_mask(accum, w, h, settings.noise_threshold) & active
            bound.update(pixel_mask=active)
        if 0 < settings.time_limit <= seconds:
            active = np.zeros_like(active)
        image = film_image(accum, w, h)
        yield RenderProgress(image, done, seconds, aovs, counts.copy(), float(active.mean()))


def render(
    scene: SceneIR | Prepared, settings: RenderSettings, backend: Backend, frame: Frame | None = None
) -> RenderProgress:
    *_, last = progressive(scene, settings, backend, frame)
    return last
