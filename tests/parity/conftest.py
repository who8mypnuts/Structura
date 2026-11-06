"""Parity-suite fixtures: every compute target available on this machine."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from structura.compute.base import BackendUnavailableError
from structura.compute.cpu import CpuBackend
from structura.compute.cuda import CudaBackend
from structura.compute.opencl import OpenCLBackend
from structura.compute.wgpu_backend import WgpuBackend
from tests.parity.glsl_runner import GlslComputeBackend

FACTORIES: dict[str, Callable[[], Any]] = {
    "cuda": CudaBackend,  # skipped without an NVIDIA driver (runs on the owner's GTX 1660)
    "opencl": OpenCLBackend,
    "wgpu": WgpuBackend,
    "glsl": GlslComputeBackend,
}


@pytest.fixture(scope="session")
def cpu() -> CpuBackend:
    return CpuBackend()


@pytest.fixture(scope="session", params=sorted(FACTORIES))
def device(request: pytest.FixtureRequest) -> Any:
    try:
        return FACTORIES[request.param]()
    except BackendUnavailableError as exc:
        pytest.skip(str(exc))
