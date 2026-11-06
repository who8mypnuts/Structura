"""Backend-neutral kernel launching (docs/11 §5).

A launch names an SKL kernel (compiled into an IR module) and supplies arguments by parameter name: numpy
arrays for Buf/BufRW parameters, Python/numpy scalars for scalar parameters.

Backends *bind* a launch: buffers are uploaded once and stay resident on the device, so progressive renders
only send the scalars that change between passes (``Bound.update``) and read back what they display.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np

from ..kernels.skl import ir
from ..kernels.skl.types import F32, I32, U32, Buffer, Scalar, SklType

SCALAR_DTYPES: dict[Scalar, type[np.generic]] = {F32: np.float32, I32: np.int32, U32: np.uint32}


class BackendUnavailableError(RuntimeError):
    """The backend's runtime (driver, device, library) is not usable on this machine."""


@dataclass(frozen=True)
class Launch:
    module: ir.Module
    kernel: str
    grid: tuple[int, int, int]
    args: Mapping[str, Any]

    @property
    def function(self) -> ir.Function:
        return self.module.functions[self.kernel]

    def params(self) -> list[tuple[str, SklType]]:
        return list(self.function.params[1:])

    def param_type(self, name: str) -> SklType:
        return dict(self.function.params)[name]

    def coerce_buffer(self, name: str, value: Any) -> np.ndarray:
        t = self.param_type(name)
        assert isinstance(t, Buffer), f"{name} is not a buffer parameter"
        return np.ascontiguousarray(value, dtype=SCALAR_DTYPES[t.elem]).ravel()

    def coerce_scalar(self, name: str, value: Any) -> np.generic:
        t = self.param_type(name)
        assert isinstance(t, Scalar), f"{name} is not a scalar parameter"
        result: np.generic = SCALAR_DTYPES[t](value)
        return result

    def buffer(self, name: str) -> np.ndarray:
        return self.coerce_buffer(name, self.args[name])

    def scalar(self, name: str) -> np.generic:
        return self.coerce_scalar(name, self.args[name])

    def buffers(self) -> list[tuple[str, Buffer]]:
        return [(n, t) for n, t in self.params() if isinstance(t, Buffer)]

    def scalars(self) -> list[str]:
        return [n for n, t in self.params() if isinstance(t, Scalar)]

    def writable(self) -> list[str]:
        return [n for n, t in self.buffers() if t.writable]

    def groups(self, grid: tuple[int, int, int] | None = None) -> tuple[int, int, int]:
        """Workgroup counts covering ``grid`` (default: the launch grid)."""
        wx, wy, wz = self.function.workgroup
        gx, gy, gz = grid or self.grid
        return -(-gx // wx), -(-gy // wy), -(-gz // wz)


class Bound(ABC):
    """A kernel with resident arguments. Subclasses implement the device-side storage."""

    def __init__(self, launch: Launch) -> None:
        self.launch = launch
        self.grid = launch.grid  # the next dispatch's grid; set_grid() narrows it (banded dispatches)
        self.scalars = {n: launch.scalar(n) for n in launch.scalars()}
        self.shapes: dict[str, tuple[int, np.dtype[Any]]] = {}
        for name, _ in launch.buffers():
            host = launch.buffer(name)
            self.shapes[name] = (host.size, host.dtype)
            self._upload(name, host)

    def update(self, **args: Any) -> None:
        """Replace some arguments. Buffers are re-uploaded; scalars are sent with the next dispatch."""
        for name, value in args.items():
            if isinstance(self.launch.param_type(name), Buffer):
                host = self.launch.coerce_buffer(name, value)
                self.shapes[name] = (host.size, host.dtype)
                self._upload(name, host)
            else:
                self.scalars[name] = self.launch.coerce_scalar(name, value)

    def set_grid(self, grid: tuple[int, int, int]) -> None:
        self.grid = grid

    def groups(self) -> tuple[int, int, int]:
        return self.launch.groups(self.grid)

    def run(self) -> dict[str, np.ndarray]:
        """Dispatch and read back every writable buffer."""
        self.dispatch()
        return {n: self.read(n) for n in self.launch.writable()}

    def ordered_args(self, buffers: Mapping[str, Any]) -> list[Any]:
        """Kernel arguments in parameter order: device buffers from `buffers`, current scalar values."""
        return [buffers[n] if n in buffers else self.scalars[n] for n, _ in self.launch.params()]

    @abstractmethod
    def _upload(self, name: str, host: np.ndarray) -> None: ...

    @abstractmethod
    def dispatch(self) -> None: ...

    @abstractmethod
    def read(self, name: str) -> np.ndarray: ...


class Backend(Protocol):
    name: str
    device_name: str
    is_gpu: bool

    def bind(self, launch: Launch) -> Bound: ...

    def run(self, launch: Launch) -> dict[str, np.ndarray]: ...


class BackendBase(ABC):
    """Shared ``run`` = bind, dispatch once, read back."""

    name = "base"
    device_name = ""
    is_gpu = False

    @abstractmethod
    def bind(self, launch: Launch) -> Bound: ...

    def run(self, launch: Launch) -> dict[str, np.ndarray]:
        return self.bind(launch).run()


def uniform_block(launch: Launch, scalars: Mapping[str, np.generic]) -> bytes:
    """Scalar kernel parameters packed as a std140 uniform block of 4-byte scalars, padded to 16 bytes."""
    data = b"".join(scalars[n].tobytes() for n in launch.scalars())
    return data + b"\0" * (-len(data) % 16 or (16 if not data else 0))
