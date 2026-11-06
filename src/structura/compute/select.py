"""Backend selection (docs/11 §6): Auto priority CUDA → OpenCL (GPU) → wgpu (GPU adapter) → CPU (Numba)."""

from __future__ import annotations

import logging
from collections.abc import Callable

from .base import Backend, BackendUnavailableError
from .cpu import CpuBackend

log = logging.getLogger(__name__)
NAMES = ("auto", "cuda", "opencl", "wgpu", "cpu")


def _cuda() -> Backend:
    from .cuda import CudaBackend  # noqa: PLC0415 - keeps the CUDA driver untouched unless requested

    return CudaBackend()


def _opencl(gpu_only: bool) -> Backend:
    from .opencl import OpenCLBackend  # noqa: PLC0415

    backend = OpenCLBackend()
    if gpu_only and not backend.is_gpu:
        raise BackendUnavailableError("OpenCL has no GPU device")
    return backend


def _wgpu(gpu_only: bool) -> Backend:
    from .wgpu_backend import WgpuBackend  # noqa: PLC0415

    backend = WgpuBackend()
    if gpu_only and not backend.is_gpu:
        raise BackendUnavailableError("wgpu adapter is a CPU (software) device")
    return backend


def select_backend(name: str = "auto") -> Backend:
    """Return the requested backend, or the best available one for 'auto'."""
    explicit: dict[str, Callable[[], Backend]] = {
        "cuda": _cuda,
        "opencl": lambda: _opencl(False),
        "wgpu": lambda: _wgpu(False),
        "cpu": CpuBackend,
    }
    if name != "auto":
        return explicit[name]()
    for candidate in (_cuda, lambda: _opencl(True), lambda: _wgpu(True)):
        try:
            return candidate()
        except BackendUnavailableError as exc:
            log.info("backend skipped: %s", exc)
    return CpuBackend()
