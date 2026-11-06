"""SKL parity: one kernel source, identical results on Numba, OpenCL, WGSL and GLSL; CUDA compiles (docs/11 §8)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from structura.compute import cuda
from structura.compute.base import Launch
from structura.compute.cpu import CpuBackend
from structura.compute.cuda import compile_ptx
from structura.kernels.skl.frontend import compile_module
from tests.parity import kernels_demo

W, H = 64, 48


def _launch() -> Launch:
    rng = np.random.default_rng(1)
    boxes = (rng.random((6, 3)) * 3 - 1.5).astype(np.float32).ravel()
    module = compile_module([kernels_demo.render_boxes])
    args = {"width": W, "height": H, "boxes": boxes, "n_boxes": 6, "result": np.zeros(W * H, np.float32)}
    return Launch(module, "render_boxes", (W, H, 1), args)


def test_numba_reference_is_sane(cpu: CpuBackend) -> None:
    image = cpu.run(_launch())["result"]
    assert 0.1 < float(image.mean()) < 0.5  # boxes (bright) over a dim noise background
    assert float((image > 0.5).mean()) > 0.1


def test_gpu_targets_match_numba(cpu: CpuBackend, device: Any) -> None:
    launch = _launch()
    reference = cpu.run(launch)["result"]
    result = device.run(launch)["result"]
    assert np.abs(result - reference).max() < 1e-5


def test_cuda_compiles_with_nvrtc() -> None:
    ptx = compile_ptx(_launch().module, "compute_75")
    assert ".entry render_boxes" in ptx


def test_cuda_images_are_machine_code_and_cached_on_disk(tmp_path: Any, monkeypatch: Any) -> None:
    monkeypatch.setattr(cuda, "CACHE", tmp_path)
    module = _launch().module
    cubin = cuda.compiled_image(module, 75)  # GTX 1660 (Turing)
    assert cubin.startswith(b"\x7fELF") and len(list(tmp_path.glob("*.bin"))) == 1
    monkeypatch.setattr(cuda, "_compile_image", lambda *_: pytest.fail("recompiled despite the cache"))
    assert cuda.compiled_image(module, 75) == cubin


def test_cuda_falls_back_to_ptx_for_architectures_nvrtc_does_not_know(tmp_path: Any, monkeypatch: Any) -> None:
    monkeypatch.setattr(cuda, "CACHE", tmp_path)
    image = cuda.compiled_image(_launch().module, 999)  # a future GPU: the driver JIT-compiles the PTX
    assert b".entry render_boxes" in image and image.endswith(b"\0")


def test_bound_launch_keeps_buffers_resident_and_accepts_updates(cpu: CpuBackend, device: Any) -> None:
    launch = _launch()
    moved = np.asarray(launch.args["boxes"]) + np.float32(0.25)
    expected = cpu.run(Launch(launch.module, launch.kernel, launch.grid, {**launch.args, "boxes": moved}))
    for backend in (cpu, device):
        bound = backend.bind(launch)
        first = bound.run()["result"]
        bound.update(boxes=moved)  # same size: written in place
        assert np.abs(bound.run()["result"] - expected["result"]).max() < 1e-5
        bound.update(n_boxes=0)  # scalar only
        assert not np.array_equal(bound.run()["result"], first)
