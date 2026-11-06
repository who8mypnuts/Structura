"""First-hit AOVs and denoising (docs/09 §6–7)."""

from __future__ import annotations

from dataclasses import replace
from functools import cache

import numpy as np
import pytest

from structura.compute.cpu import CpuBackend
from structura.core.build.api import build_scene
from structura.core.lang.api import compile_script
from structura.core.scene.ir import SceneIR
from structura.render.api import RenderProgress, prepare, render
from structura.render.denoise import denoise
from structura.render.denoise.oidn import OidnUnavailableError, library
from structura.render.settings import RenderSettings

SCRIPT = "set background #fff\n{ x -0.6 s 1.2 color #f00 } box\n{ x 0.6 s 1.2 color #0f0 } sphere\n"


@cache
def _scene() -> SceneIR:
    return build_scene(compile_script(SCRIPT).program).scene


def _render(samples: int, aovs: bool = False) -> RenderProgress:
    settings = RenderSettings(width=48, height=32, samples=samples, samples_per_pass=min(samples, 32),
                              integrator="path", frame=True, aovs=aovs, seed=samples)  # fmt: skip
    return render(prepare(_scene()), settings, CpuBackend())


def test_aovs_describe_the_first_hits() -> None:
    aovs = _render(1, aovs=True).aovs
    assert aovs is not None
    hit = aovs.alpha > 0.5
    assert 0.1 < hit.mean() < 0.9 and np.all(np.isinf(aovs.depth[aovs.alpha == 0]))
    assert set(np.unique(aovs.instance[hit])) <= {0, 1} and set(np.unique(aovs.instance[~hit])) <= {-1, 0, 1}
    box = aovs.instance == 0
    assert aovs.albedo[box][:, 0].mean() > 0.5 and aovs.albedo[box][:, 1].mean() < 0.1  # red, linear
    length = np.linalg.norm(aovs.normal[hit], axis=1)
    assert np.allclose(length, 1.0, atol=1e-3)
    assert set(aovs.layers()) == {"albedo", "N", "Z", "A", "instance", "material"}


def _eroded(mask: np.ndarray, steps: int) -> np.ndarray:
    for _ in range(steps):
        p = np.pad(mask, 1)
        mask = p[1:-1, 1:-1] & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    return mask


def test_atrous_denoising_gets_closer_to_the_converged_image() -> None:
    noisy = _render(4, aovs=True)
    reference = _render(256).image
    assert noisy.aovs is not None
    cleaned, method = denoise(noisy.image, noisy.aovs.albedo, noisy.aovs.normal, method="atrous")
    inside = _eroded(noisy.aovs.alpha > 0.5, 2)  # silhouettes are dominated by anti-aliasing, not noise

    def rmse(image: np.ndarray, mask: np.ndarray | slice = slice(None)) -> float:
        return float(np.sqrt(((image - reference) ** 2)[mask].mean()))

    assert method == "atrous" and rmse(cleaned, inside) < 0.6 * rmse(noisy.image, inside)
    assert rmse(cleaned) < 1.1 * rmse(noisy.image)
    assert float(cleaned.mean()) == pytest.approx(float(reference.mean()), rel=0.05)  # no brightness shift


def test_auto_falls_back_when_open_image_denoise_is_missing() -> None:
    image = np.random.default_rng(0).random((8, 8, 3)).astype(np.float32)
    try:
        library()
    except OidnUnavailableError:
        assert denoise(image, method="auto")[1] == "atrous"
        with pytest.raises(OidnUnavailableError):
            denoise(image, method="oidn")
    else:  # pragma: no cover - only where the library is installed
        out, method = denoise(image, method="auto")
        assert method == "oidn" and out.shape == image.shape


def test_settings_default_to_no_aovs() -> None:
    assert RenderSettings().aovs is False and replace(RenderSettings(), aovs=True).aovs
