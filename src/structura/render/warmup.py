"""Kernel warm-up (docs/04 §6 rule 5, docs/11 §7): compile every Numba kernel once so that the first build
and render never wait on the JIT. Installers run `structura warmup`; the GUI runs the same steps as a
background job at start-up. Each step is cheap once the on-disk caches exist."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator

import numpy as np

from ..compute.base import Backend
from ..core.build.api import build_scene
from ..core.lang.api import compile_script
from .api import prepare_with_frame, progressive
from .denoise.atrous import atrous_denoise
from .settings import INTEGRATORS, RenderSettings

SCRIPT = (
    "#version 2\n{ x 1 color #f80 } box\nsphere\n{ x 2 } cone[0.5]\n{ y 2 } torus\n"
    "{ y -2 } triangle[0,0,0;1,0,0;0,1,0]\n"
)  # every primitive kind the kernels branch on
Step = tuple[str, Callable[[], object]]


def _render(backend: Backend, integrator: str) -> Callable[[], object]:
    def run() -> object:
        scene = build_scene(compile_script(SCRIPT).program).scene
        settings = RenderSettings(width=8, height=8, samples=1, samples_per_pass=1, integrator=integrator,
                                  frame=True, aovs=integrator == "path")  # fmt: skip
        prepared, frame = prepare_with_frame(scene, settings)
        return list(progressive(prepared, settings, backend, frame))

    return run


def steps(backend: Backend) -> list[Step]:
    image = np.zeros((8, 8, 3), np.float32)
    return [
        ("builder", lambda: build_scene(compile_script(SCRIPT).program).scene),
        *((f"render {name} ({backend.name})", _render(backend, name)) for name in INTEGRATORS),
        ("denoiser", lambda: atrous_denoise(image, image, image)),
    ]


def warm_up(backend: Backend) -> Iterator[tuple[str, float]]:
    """Run every step; yields (step, seconds) as each one finishes."""
    for name, step in steps(backend):
        started = time.perf_counter()
        step()
        yield name, time.perf_counter() - started
