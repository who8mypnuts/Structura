"""OpenCL backend (pyopencl). Prefers GPU devices; pocl's CPU device is used when no GPU exists (CI)."""

from __future__ import annotations

from functools import cache
from typing import Any

import numpy as np
import pyopencl as cl

from ..kernels.skl.emit.opencl import OpenCLEmitter
from .base import BackendBase, BackendUnavailableError, Bound, Launch


@cache
def _context(prefer_gpu: bool = True) -> tuple[Any, Any]:
    devices = [d for p in cl.get_platforms() for d in p.get_devices()]
    if not devices:
        raise BackendUnavailableError("no OpenCL devices")
    gpus = [d for d in devices if d.type & cl.device_type.GPU]
    device = (gpus or devices)[0] if prefer_gpu else devices[0]
    ctx = cl.Context([device])
    return ctx, cl.CommandQueue(ctx)


class OpenCLBound(Bound):
    def __init__(self, backend: OpenCLBackend, launch: Launch) -> None:
        self.backend = backend
        self.kernel = backend.kernel(launch)
        self.device: dict[str, Any] = {}
        super().__init__(launch)

    def _upload(self, name: str, host: np.ndarray) -> None:
        old = self.device.get(name)
        if old is not None and old.size == host.nbytes:
            cl.enqueue_copy(self.backend.queue, old, host)
            return
        flags = cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR
        self.device[name] = cl.Buffer(self.backend.ctx, flags, hostbuf=host if host.size else np.zeros(1, host.dtype))

    def dispatch(self) -> None:
        wg = self.launch.function.workgroup
        global_size = tuple(g * w for g, w in zip(self.groups(), wg, strict=True))
        self.kernel(self.backend.queue, global_size, wg, *self.ordered_args(self.device))

    def finish(self) -> None:
        self.backend.queue.finish()

    def read(self, name: str) -> np.ndarray:
        size, dtype = self.shapes[name]
        result = np.empty(size, dtype)
        cl.enqueue_copy(self.backend.queue, result, self.device[name])
        self.backend.queue.finish()
        return result


class OpenCLBackend(BackendBase):
    name = "opencl"

    def __init__(self) -> None:
        self.ctx, self.queue = _context()
        self.device_name = str(self.ctx.devices[0].name)
        self.is_gpu = bool(self.ctx.devices[0].type & cl.device_type.GPU)
        self._programs: dict[str, Any] = {}

    def kernel(self, launch: Launch) -> Any:
        source = OpenCLEmitter(launch.module).emit()
        if source not in self._programs:
            self._programs[source] = cl.Program(self.ctx, source).build(options=["-cl-std=CL1.2"])
        return cl.Kernel(self._programs[source], launch.kernel)  # one Kernel per binding: args are per-object

    def bind(self, launch: Launch) -> Bound:
        return OpenCLBound(self, launch)
