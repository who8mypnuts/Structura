"""First-hit AOVs for a render (docs/09 §6): run the aov_pass kernel once and resolve its sums into images."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache

import numpy as np

from ..compute.base import Backend, Launch
from ..kernels.skl import ir
from ..kernels.skl.frontend import compile_module
from .kernels.aov import AOV_F, aov_pass

AOV_SAMPLES = 16


@cache
def aov_module() -> ir.Module:
    return compile_module([aov_pass])


@dataclass(frozen=True)
class Aovs:
    albedo: np.ndarray  # float32 (H, W, 3), linear
    normal: np.ndarray  # float32 (H, W, 3), world space, unit (0 where nothing was hit)
    depth: np.ndarray  # float32 (H, W), camera-ray distance (inf where nothing was hit)
    alpha: np.ndarray  # float32 (H, W), coverage
    instance: np.ndarray  # int64 (H, W), SceneIR row (-1 for the background)
    material: np.ndarray  # int64 (H, W), material index (-1 for the background)

    def layers(self) -> dict[str, np.ndarray]:
        """EXR layers (float32; ids as float so every viewer shows them)."""
        return {"albedo": self.albedo, "N": self.normal, "Z": self.depth.astype(np.float32),
                "A": self.alpha, "instance": self.instance.astype(np.float32),
                "material": self.material.astype(np.float32)}  # fmt: skip


def resolve(raw: np.ndarray, width: int, height: int, samples: int) -> Aovs:
    r = raw.reshape(height, width, AOV_F)
    hits = r[..., 7]
    inv = np.where(hits > 0, 1.0 / np.maximum(hits, 1.0), 0.0)[..., None]
    normal = r[..., 3:6] * inv
    length = np.linalg.norm(normal, axis=-1, keepdims=True)
    normal = np.where(length > 1e-6, normal / np.maximum(length, 1e-6), 0.0)
    depth = np.where(hits > 0, r[..., 6] * inv[..., 0], np.inf)
    return Aovs((r[..., 0:3] * inv).astype(np.float32), normal.astype(np.float32), depth.astype(np.float32),
                (hits / max(samples, 1)).astype(np.float32), r[..., 8].astype(np.int64) - 1,
                r[..., 9].astype(np.int64) - 1)  # fmt: skip


def render_aovs(args: dict[str, object], backend: Backend, samples: int = AOV_SAMPLES) -> Aovs:
    """``args``: the beauty pass's launch arguments (the scene buffers and cfg are shared)."""
    width, height = int(args["width"]), int(args["height"])  # type: ignore[call-overload]
    names = {p for p, _ in Launch(aov_module(), "aov_pass", (1, 1, 1), {}).params()}
    kernel_args = {k: v for k, v in args.items() if k in names}
    kernel_args |= {"aov": np.zeros(width * height * AOV_F, np.float32), "sample_base": 0, "spp": samples}
    bound = backend.bind(Launch(aov_module(), "aov_pass", (width, height, 1), kernel_args))
    bound.dispatch()
    return resolve(bound.read("aov"), width, height, samples)
