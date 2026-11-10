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
from .aovs import render_aovs
from .bands import Bands
from .bvh import Bvh, build_bvh
from .config import Frame, config, scene_frame, with_legacy_dof
from .declarations import declared_settings
from .emitters import Emitters, pack_emitters
from .environment import settings_environment
from .film import active_mask, initial_mask, new_film
from .ground import Ground, with_ground
from .kernels.layout import MAX_GENERATION, N_EMITTERS
from .kernels.passes import render_pass
from .kernels.scene import PF_GENERATION
from .legacy import with_legacy
from .lights import pack_lights
from .materials import pack_materials
from .mosaic import mosaic_pass
from .pacing import Pacing
from .pack import PackedScene, PackOptions, pack_scene
from .photons import add_photons
from .progress import RenderProgress, RenderRun
from .settings import INTEGRATORS, RenderSettings
from .tiled import tiled_passes

Phase = Callable[[str], None]  # told what a render is doing before its first pass ("Building the BVH…")


def _quiet(_text: str) -> None:
    """The default phase callback: says nothing."""


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


def prepare(
    scene: SceneIR, declared: Mapping[str, Material] | None = None, tag_presets: bool = False,
    ground: Ground | None = None, phase: Phase = _quiet,
) -> Prepared:  # fmt: skip
    """Packs the scene, builds the BVH and resolves the materials.

    Materials come from the ``declared`` ones, then presets named like a tag if enabled. v2 scripts bring their
    own 'material' blocks and always enable tag presets (docs/05 §9.3).

    Args:
        scene: The built scene.
        declared: Materials by tag, over the script's own.
        tag_presets: Whether a tag named like a preset ('box::glass') uses it.
        ground: A ground plane or shadow catcher to add under the scene (excluded from the framing bounds).
        phase: Told what is happening ('Building the BVH…'), for progress displays.

    Returns:
        Everything the kernels need of the scene.
    """
    if scene.declarations is not None:
        declared, tag_presets = {**scene.declarations.materials, **(declared or {})}, True
    scene_settings = settings_from_events(scene.events)
    materials = resolve_materials(scene.tags, scene_settings.raytracer, declared, tag_presets)
    phase(f"Packing {len(scene):,} objects…")
    packed = pack_scene(scene, PackOptions(material_of_tag=materials.by_tag))
    if len(packed):
        lo, hi = packed.lo.min(axis=0), packed.hi.max(axis=0)
    else:
        lo, hi = np.full(3, -1.0, np.float32), np.full(3, 1.0, np.float32)
    if ground is not None:
        packed, materials = with_ground(packed, materials, ground, len(scene), lo, hi)
    phase(f"Building the BVH over {len(packed):,} primitives…")
    bvh = build_bvh(packed.lo, packed.hi)
    emitters = pack_emitters(packed, pack_materials(materials), scene.xform)
    return Prepared(packed, bvh, materials, emitters, scene_settings, scene.declarations, lo, hi)


def prepare_with_frame(
    scene: SceneIR, settings: RenderSettings, tag_presets: bool = False, camera: Camera | None = None,
    phase: Phase = _quiet,
) -> tuple[Prepared, Frame]:  # fmt: skip
    """Prepares a scene and its view.

    Args:
        scene: The built scene.
        settings: The render settings (their ground is added).
        tag_presets: Whether a tag named like a preset uses it.
        camera: The camera to render with; None uses the script's camera, or frames the structure. Legacy
            'raytracer::dof' settings still apply to a given camera without depth of field.
        phase: Told what is happening, for progress displays.

    Returns:
        (the prepared scene, its frame: camera, settings and scale).
    """
    prepared = prepare(scene, tag_presets=tag_presets, ground=settings.ground_spec, phase=phase)
    frame = scene_frame(prepared.scene_settings, settings, prepared.lo, prepared.hi, prepared.declarations)
    if camera is None:
        return prepared, frame
    return prepared, replace(frame, camera=with_legacy_dof(camera, settings, prepared.scene_settings))


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
    """Returns the render kernel's arguments: buffers, the configuration and the film.

    Args:
        prepared: The prepared scene.
        frame: The view and settings.
    """
    st, p, b = frame.settings, prepared.packed, prepared.bvh
    env = settings_environment(st)
    cfg = config(frame)
    cfg[N_EMITTERS] = len(prepared.emitters)  # the count lives with the scene, the rest of cfg with the frame
    cfg[MAX_GENERATION] = float(p.prim_f[:, PF_GENERATION].max()) if len(p) else 0.0
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
        "col0": 0,
        "sample_base": 0,
        "spp": 0,
    }


def _resumed(args: dict[str, Any], w: int, h: int, resume: RenderProgress | None) -> tuple[np.ndarray, int, float]:
    """(samples per pixel, samples done, seconds spent): zero, or where a stopped render left off. The film and
    the pixel mask go back into ``args``; sample indices continue, so the result equals an uninterrupted render."""
    if resume is None or resume.film is None:
        return np.zeros((h, w), np.int32), 0, 0.0
    args["accum"] = resume.film.copy()
    if resume.mask is not None:
        args["pixel_mask"] = resume.mask.copy()
    counts = resume.sample_map.copy() if resume.sample_map is not None else np.full((h, w), resume.samples, np.int32)
    return counts, resume.samples, resume.seconds


def start_run(
    prepared: Prepared, settings: RenderSettings, backend: Backend, frame: Frame, resume: RenderProgress | None,
    phase: Phase = _quiet,
) -> tuple[RenderRun, np.ndarray]:  # fmt: skip
    """Binds the render kernel, after the photon and AOV passes when they are asked for.

    Args:
        prepared: The prepared scene.
        settings: The render settings.
        backend: The compute backend.
        frame: The view.
        resume: A stopped render of the same scene, camera and settings to continue, or None.
        phase: Told what is happening, for progress displays.

    Returns:
        (the run, the starting film: empty, or the resumed one).
    """
    w, h = settings.width, settings.height
    args = launch_args(prepared, frame)
    if settings.caustics == "photons":
        phase(f"Tracing {settings.photon_count:,} caustic photons…")
        add_photons(args, prepared.lo, prepared.hi, settings.photon_count, settings.photon_radius, backend,
                    settings.seed)  # fmt: skip
    aovs = resume.aovs if resume is not None else None
    if settings.aovs and aovs is None:
        phase("First-hit passes (albedo, normals, depth)…")
        aovs = render_aovs(args, backend)
    counts, done, spent = _resumed(args, w, h, resume)
    film = args["accum"].copy()
    phase(f"Starting the render kernel on {backend.name} (the first render on a device compiles it)…")
    started = time.perf_counter()
    bound = backend.bind(Launch(render_module(), "render_pass", (w, h, 1), args))
    run = RenderRun(settings, bound, args["pixel_mask"], counts, done, spent, aovs)
    run.bind_seconds = time.perf_counter() - started
    return run, film


def progressive(
    scene: SceneIR | Prepared,
    settings: RenderSettings,
    backend: Backend,
    frame: Frame | None = None,
    between: Callable[[], None] | None = None,
    resume: RenderProgress | None = None,
    phase: Phase = _quiet,
) -> Iterator[RenderProgress]:
    """Renders pass by pass, yielding the image after every pass.

    Passes are sized by render/pacing.py; the tiled sampler yields after buckets instead (render/tiled.py). The
    render stops at ``settings.samples``, at the time limit, or when adaptive sampling finds every pixel below the
    noise threshold.

    Args:
        scene: A built scene, or one prepared already.
        settings: The render settings.
        backend: The compute backend.
        frame: The view; None uses the script's camera or framing.
        between: Runs between the row bands of each pass (cancellation checks).
        resume: A stopped render of the same scene, camera and settings to continue.
        phase: Told what is happening before the first pass.

    Yields:
        The progress after each pass (image, samples, timings).
    """
    prepared = scene if isinstance(scene, Prepared) else prepare(scene)
    frame = frame or scene_frame(prepared.scene_settings, settings, prepared.lo, prepared.hi, prepared.declarations)
    run, film = start_run(prepared, settings, backend, frame, resume, phase)
    if settings.sampler == "tiled":
        yield from tiled_passes(run, film, between)
        return
    if settings.mosaic and resume is None and settings.region is None:
        yield mosaic_pass(run, between)
    yield from _passes(run, between)


def _passes(run: RenderRun, between: Callable[[], None] | None) -> Iterator[RenderProgress]:
    """The progressive sampler's passes (see ``progressive``)."""
    s, (w, h) = run.settings, run.size
    bands, pacing = Bands(w, h), Pacing(s)
    while run.done < s.samples and run.mask.any():
        started = time.perf_counter()
        spp = pacing.next(run.done)
        run.bound.update(sample_base=run.sample_base(run.done), spp=spp)
        pacing.observe(spp, bands.dispatch(run.bound, between))
        run.done += spp
        run.counts += run.mask.reshape(h, w).astype(np.int32) * spp
        accum = run.bound.read("accum")
        if s.noise_threshold > 0 and run.done >= s.adaptive_min_samples:
            run.mask = active_mask(accum, w, h, s.noise_threshold) & run.mask
            run.bound.update(pixel_mask=run.mask)
        if run.out_of_time():
            run.mask = np.zeros_like(run.mask)
        run.pass_times.append(time.perf_counter() - started)
        yield replace(run.snapshot(accum), samples=run.done)


def render(
    scene: SceneIR | Prepared, settings: RenderSettings, backend: Backend, frame: Frame | None = None
) -> RenderProgress:
    """Renders to completion.

    Args:
        scene: A built scene, or one prepared already.
        settings: The render settings.
        backend: The compute backend.
        frame: The view; None uses the script's camera or framing.

    Returns:
        The final progress (the finished image).
    """
    *_, last = progressive(scene, settings, backend, frame)
    return last


__all__ = [
    "Prepared",
    "RenderProgress",
    "launch_args",
    "prepare",
    "prepare_with_frame",
    "progressive",
    "render",
    "render_module",
    "script_settings",
    "start_run",
]
