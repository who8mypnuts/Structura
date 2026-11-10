"""The CUDA emission of every render kernel compiles with NVRTC (no NVIDIA GPU needed): the parity tests
that run CUDA only exist on a machine with one."""

from __future__ import annotations

import pytest

from structura.compute import cuda
from structura.kernels.skl.frontend import compile_module
from structura.render.kernels.aov import aov_pass
from structura.render.kernels.passes import render_pass
from structura.render.kernels.photons import photon_pass


@pytest.mark.skipif(cuda.nvrtc is None, reason="NVRTC (nvidia-cuda-nvrtc) is not installed")
@pytest.mark.parametrize("kernel", [render_pass, aov_pass, photon_pass], ids=lambda k: k.__name__)
def test_render_kernels_compile_to_ptx(kernel: object) -> None:
    try:
        ptx = cuda.compile_ptx(compile_module([kernel]), "compute_75")
    except RuntimeError as exc:
        if "libnvrtc" in str(exc) or "not found" in str(exc).lower():
            pytest.skip(f"NVRTC library unavailable: {exc}")
        raise
    assert ".entry" in ptx
