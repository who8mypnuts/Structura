"""Run an SKL kernel as a GLSL 430 compute shader through ModernGL (EGL, Mesa llvmpipe in CI).

The preview engine only uses GLSL *function libraries*; running whole kernels here lets the parity suite
check the GLSL emitter against the other targets.
"""

from __future__ import annotations

from functools import cache
from typing import Any

import moderngl
import numpy as np

from structura.compute.base import BackendBase, BackendUnavailableError, Bound, Launch
from structura.kernels.skl.emit.glsl import GLSLEmitter


@cache
def _context() -> Any:
    try:
        return moderngl.create_standalone_context(require=430, backend="egl")
    except Exception as exc:
        raise BackendUnavailableError(f"no OpenGL 4.3 context: {exc}") from exc


class GlslBound(Bound):
    def __init__(self, launch: Launch) -> None:
        self.ctx = _context()
        self.shader = self.ctx.compute_shader(GLSLEmitter(launch.module).emit())
        self.gpu: dict[str, Any] = {}
        super().__init__(launch)

    def _upload(self, name: str, host: np.ndarray) -> None:
        self.gpu[name] = self.ctx.buffer(host.tobytes() or b"\0\0\0\0")

    def dispatch(self) -> None:
        for binding, (name, _) in enumerate(self.launch.buffers()):
            self.gpu[name].bind_to_storage_buffer(binding)
        for name, value in self.scalars.items():
            if name in self.shader:
                self.shader[name] = value.item()
        self.shader.run(*self.launch.groups())

    def read(self, name: str) -> np.ndarray:
        self.ctx.finish()
        size, dtype = self.shapes[name]
        return np.frombuffer(self.gpu[name].read(), dtype=dtype)[:size].copy()


class GlslComputeBackend(BackendBase):
    name = "glsl"
    device_name = "OpenGL 4.3 compute"

    def bind(self, launch: Launch) -> Bound:
        return GlslBound(launch)
