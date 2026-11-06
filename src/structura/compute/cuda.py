"""CUDA backend: SKL → CUDA C++ → NVRTC (PTX) → driver API via cuda-python (docs/11 §5).

``compile_ptx`` works without a GPU (used in CI); ``run`` needs an NVIDIA driver and device.
"""

from __future__ import annotations

from typing import Any

import numpy as np

try:  # cuda-python is not installed on macOS (CUDA does not exist there)
    from cuda.bindings import driver, nvrtc
except ImportError:  # pragma: no cover
    driver = nvrtc = None

from ..kernels.skl import ir
from ..kernels.skl.emit.cuda import CudaEmitter
from .base import BackendBase, BackendUnavailableError, Bound, Launch


def _check(result: tuple[Any, ...], what: str) -> Any:
    err, *rest = result
    if int(err) != 0:
        raise RuntimeError(f"{what} failed: {err}")
    return rest[0] if len(rest) == 1 else rest


def compile_ptx(module: ir.Module, arch: str = "compute_75") -> str:
    if nvrtc is None:
        raise BackendUnavailableError("cuda-python/NVRTC is not installed")
    source = CudaEmitter(module).emit().encode()
    prog = _check(nvrtc.nvrtcCreateProgram(source, b"skl.cu", 0, [], []), "nvrtcCreateProgram")
    exact = any(f.exact for f in module.functions.values())
    options = [f"--gpu-architecture={arch}".encode(), b"--std=c++17"] + ([b"--fmad=false"] if exact else [])
    (err,) = nvrtc.nvrtcCompileProgram(prog, len(options), options)
    if int(err) != 0:
        size = _check(nvrtc.nvrtcGetProgramLogSize(prog), "log size")
        log = b" " * size
        nvrtc.nvrtcGetProgramLog(prog, log)
        raise RuntimeError("NVRTC compilation failed:\n" + log.decode(errors="replace"))
    size = _check(nvrtc.nvrtcGetPTXSize(prog), "nvrtcGetPTXSize")
    ptx = b" " * size
    _check((nvrtc.nvrtcGetPTX(prog, ptx)[0], None), "nvrtcGetPTX")
    return str(ptx.decode(errors="replace").rstrip("\0"))


class CudaBound(Bound):  # pragma: no cover - needs an NVIDIA GPU
    def __init__(self, backend: CudaBackend, launch: Launch) -> None:
        self.backend = backend
        backend.activate()
        self.function = backend.function(launch)
        self.device: dict[str, tuple[Any, int]] = {}  # name -> (device pointer, capacity in bytes)
        super().__init__(launch)

    def _upload(self, name: str, host: np.ndarray) -> None:
        self.backend.activate()
        ptr, capacity = self.device.get(name, (None, 0))
        if ptr is None or capacity < host.nbytes:
            if ptr is not None:
                driver.cuMemFree(ptr)
            capacity = max(4, host.nbytes)
            ptr = _check(driver.cuMemAlloc(capacity), "cuMemAlloc")
            self.device[name] = (ptr, capacity)
        if host.nbytes:
            _check((driver.cuMemcpyHtoD(ptr, host.ctypes.data, host.nbytes)[0], None), "HtoD")

    def dispatch(self) -> None:
        self.backend.activate()
        pointers = {n: np.array([int(p)], dtype=np.uint64) for n, (p, _) in self.device.items()}
        values = [v if isinstance(v, np.ndarray) else np.array([v]) for v in self.ordered_args(pointers)]
        params = np.array([v.ctypes.data for v in values], dtype=np.uint64)
        wg = self.launch.function.workgroup
        launch = driver.cuLaunchKernel(self.function, *self.groups(), *wg, 0, 0, params.ctypes.data, 0)
        _check((launch[0], None), "cuLaunchKernel")

    def read(self, name: str) -> np.ndarray:
        size, dtype = self.shapes[name]
        result = np.empty(size, dtype)
        self.backend.activate()
        if result.nbytes:
            _check((driver.cuMemcpyDtoH(result.ctypes.data, self.device[name][0], result.nbytes)[0], None), "DtoH")
        return result

    def __del__(self) -> None:
        for ptr, _ in getattr(self, "device", {}).values():
            driver.cuMemFree(ptr)


def _attribute(device: Any, name: str) -> int:
    return int(_check(driver.cuDeviceGetAttribute(getattr(driver.CUdevice_attribute, name), device), name))


class CudaBackend(BackendBase):
    name = "cuda"
    is_gpu = True

    def __init__(self) -> None:
        if driver is None:
            raise BackendUnavailableError("cuda-python is not installed")
        try:
            _check(driver.cuInit(0), "cuInit")
            self.device = _check(driver.cuDeviceGet(0), "cuDeviceGet")
        except Exception as exc:
            raise BackendUnavailableError(f"no CUDA device: {exc}") from exc
        self.ctx = _check(driver.cuDevicePrimaryCtxRetain(self.device), "cuDevicePrimaryCtxRetain")  # pragma: no cover
        self.activate()  # pragma: no cover
        major = _attribute(self.device, "CU_DEVICE_ATTRIBUTE_COMPUTE_CAPABILITY_MAJOR")  # pragma: no cover
        minor = _attribute(self.device, "CU_DEVICE_ATTRIBUTE_COMPUTE_CAPABILITY_MINOR")  # pragma: no cover
        self.arch = f"compute_{major}{minor}"  # pragma: no cover
        name = _check(driver.cuDeviceGetName(128, self.device), "cuDeviceGetName")  # pragma: no cover
        self.device_name = bytes(name).split(b"\0")[0].decode()  # pragma: no cover
        self._functions: dict[tuple[str, str], Any] = {}  # pragma: no cover

    def activate(self) -> None:  # pragma: no cover - needs an NVIDIA GPU
        """Make the primary context current on the calling thread (render workers run off the GUI thread)."""
        _check((driver.cuCtxSetCurrent(self.ctx)[0], None), "cuCtxSetCurrent")

    def function(self, launch: Launch) -> Any:  # pragma: no cover - needs an NVIDIA GPU
        key = (CudaEmitter(launch.module).emit(), launch.kernel)
        if key not in self._functions:
            ptx = compile_ptx(launch.module, self.arch).encode() + b"\0"
            module = _check(driver.cuModuleLoadData(ptx), "cuModuleLoadData")
            self._functions[key] = _check(driver.cuModuleGetFunction(module, launch.kernel.encode()), "function")
        return self._functions[key]

    def bind(self, launch: Launch) -> Bound:  # pragma: no cover - needs an NVIDIA GPU
        return CudaBound(self, launch)
