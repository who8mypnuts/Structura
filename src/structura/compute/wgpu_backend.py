"""WGSL backend (wgpu-py, offscreen compute). Bindings: buffers in parameter order, then the uniform block."""

from __future__ import annotations

from functools import cache
from typing import Any

import numpy as np
import wgpu

from ..kernels.skl.emit.wgsl import WGSLEmitter
from .base import BackendBase, BackendUnavailableError, Bound, Launch, uniform_block

STORAGE = wgpu.BufferUsage.STORAGE | wgpu.BufferUsage.COPY_SRC | wgpu.BufferUsage.COPY_DST
UNIFORM = wgpu.BufferUsage.UNIFORM | wgpu.BufferUsage.COPY_DST


@cache
def _device() -> Any:
    adapter = wgpu.gpu.request_adapter_sync(power_preference="high-performance")
    if adapter is None:
        raise BackendUnavailableError("no wgpu adapter")
    limits = adapter.limits
    device = adapter.request_device_sync(
        required_limits={
            "max-storage-buffer-binding-size": limits["max-storage-buffer-binding-size"],
            "max-buffer-size": limits["max-buffer-size"],
        }
    )
    return device, adapter.info


def _entry(binding: int, buf: Any) -> dict[str, Any]:
    return {"binding": binding, "resource": {"buffer": buf, "offset": 0, "size": buf.size}}


class WgpuBound(Bound):
    def __init__(self, backend: WgpuBackend, launch: Launch) -> None:
        self.device = backend.device
        self.pipeline = backend.pipeline(WGSLEmitter(launch.module).emit(), launch)
        self.gpu: dict[str, Any] = {}
        self.bind_group: Any = None
        super().__init__(launch)
        block = uniform_block(launch, self.scalars)
        self.uniform = self.device.create_buffer(size=len(block), usage=UNIFORM) if launch.scalars() else None

    def _upload(self, name: str, host: np.ndarray) -> None:
        data = host.tobytes() or b"\0\0\0\0"
        old = self.gpu.get(name)
        if old is not None and old.size == len(data):
            self.device.queue.write_buffer(old, 0, data)
            return
        self.gpu[name] = self.device.create_buffer_with_data(data=data, usage=STORAGE)
        self.bind_group = None  # a buffer was replaced: rebuild the bind group

    def _bind_group(self) -> Any:
        if self.bind_group is None:
            entries = [_entry(i, self.gpu[n]) for i, (n, _) in enumerate(self.launch.buffers())]
            if self.uniform is not None:
                entries.append(_entry(len(entries), self.uniform))
            layout = self.pipeline.get_bind_group_layout(0)
            self.bind_group = self.device.create_bind_group(layout=layout, entries=entries)
        return self.bind_group

    def dispatch(self) -> None:
        if self.uniform is not None:
            self.device.queue.write_buffer(self.uniform, 0, uniform_block(self.launch, self.scalars))
        encoder = self.device.create_command_encoder()
        pass_ = encoder.begin_compute_pass()
        pass_.set_pipeline(self.pipeline)
        pass_.set_bind_group(0, self._bind_group())
        pass_.dispatch_workgroups(*self.groups())
        pass_.end()
        self.device.queue.submit([encoder.finish()])

    def finish(self) -> None:
        # wgpu-py 0.32's on_submitted_work_done_sync() is broken (callback signature); reading four bytes back
        # waits for the queue just the same.
        self.device.queue.read_buffer(self.gpu[self.launch.writable()[0]], 0, 4)

    def read(self, name: str) -> np.ndarray:
        size, dtype = self.shapes[name]
        return np.frombuffer(self.device.queue.read_buffer(self.gpu[name]), dtype=dtype)[:size].copy()


class WgpuBackend(BackendBase):
    name = "wgpu"

    def __init__(self) -> None:
        self.device, info = _device()
        self.device_name = str(info.get("device", ""))
        self.is_gpu = str(info.get("adapter_type", "")).lower() not in ("cpu", "unknown")
        self._pipelines: dict[tuple[str, str], Any] = {}

    def pipeline(self, source: str, launch: Launch) -> Any:
        key = (source, launch.kernel)
        if key not in self._pipelines:
            shader = self.device.create_shader_module(code=source)
            self._pipelines[key] = self.device.create_compute_pipeline(
                layout=self._layout(launch), compute={"module": shader, "entry_point": launch.kernel}
            )
        return self._pipelines[key]

    def _layout(self, launch: Launch) -> Any:
        """The layout of every declared binding. ('auto' would keep only the bindings the shader uses, so a
        kernel that ignores part of a buffer set could not be bound with the whole set.)"""
        compute, types = wgpu.ShaderStage.COMPUTE, wgpu.BufferBindingType
        entries = [{"binding": i, "visibility": compute,
                    "buffer": {"type": types.storage if t.writable else types.read_only_storage}}
                   for i, (_, t) in enumerate(launch.buffers())]  # fmt: skip
        if launch.scalars():
            entries.append({"binding": len(entries), "visibility": compute, "buffer": {"type": types.uniform}})
        group = self.device.create_bind_group_layout(entries=entries)
        return self.device.create_pipeline_layout(bind_group_layouts=[group])

    def bind(self, launch: Launch) -> Bound:
        return WgpuBound(self, launch)
