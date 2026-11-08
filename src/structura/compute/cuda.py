"""CUDA backend: SKL → CUDA C++ → NVRTC (PTX) → driver API via cuda-python (docs/11 §5).

``compile_ptx`` works without a GPU (used in CI); ``run`` needs an NVIDIA driver and device.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
from pathlib import Path
from typing import Any

import numpy as np
import platformdirs

try:  # cuda-python is not installed on macOS (CUDA does not exist there)
    from cuda.bindings import driver, nvrtc
except ImportError:  # pragma: no cover
    driver = nvrtc = None

from ..kernels.skl import ir
from ..kernels.skl.emit.cuda import CudaEmitter
from .base import BackendBase, BackendUnavailableError, Bound, Launch

CACHE = Path(platformdirs.user_cache_dir("structura")) / "cuda"


def _check(result: tuple[Any, ...], what: str) -> Any:
    err, *rest = result
    if int(err) != 0:
        raise RuntimeError(f"{what} failed: {err}")
    return rest[0] if len(rest) == 1 else rest


def _program(source: bytes, options: list[bytes]) -> Any:
    prog = _check(nvrtc.nvrtcCreateProgram(source, b"skl.cu", 0, [], []), "nvrtcCreateProgram")
    (err,) = nvrtc.nvrtcCompileProgram(prog, len(options), options)
    if int(err) != 0:
        size = _check(nvrtc.nvrtcGetProgramLogSize(prog), "log size")
        log = b" " * size
        nvrtc.nvrtcGetProgramLog(prog, log)
        raise RuntimeError("NVRTC compilation failed:\n" + log.decode(errors="replace"))
    return prog


def _options(module: ir.Module, arch: str) -> list[bytes]:
    exact = any(f.exact for f in module.functions.values())
    return [f"--gpu-architecture={arch}".encode(), b"--std=c++17"] + ([b"--fmad=false"] if exact else [])


def compile_ptx(module: ir.Module, arch: str = "compute_75") -> str:
    if nvrtc is None:
        raise BackendUnavailableError("cuda-python/NVRTC is not installed")
    prog = _program(CudaEmitter(module).emit().encode(), _options(module, arch))
    size = _check(nvrtc.nvrtcGetPTXSize(prog), "nvrtcGetPTXSize")
    ptx = b" " * size
    _check((nvrtc.nvrtcGetPTX(prog, ptx)[0], None), "nvrtcGetPTX")
    return str(ptx.decode(errors="replace").rstrip("\0"))


def _supported_archs() -> list[int]:
    return [int(a) for a in _check(nvrtc.nvrtcGetSupportedArchs(), "nvrtcGetSupportedArchs")]


def _compile_image(module: ir.Module, capability: int) -> bytes:
    """Machine code (CUBIN) for the device when NVRTC knows its architecture; otherwise PTX for the newest
    architecture NVRTC knows that the device can run (the driver JIT-compiles it, e.g. a brand-new GPU)."""
    archs = _supported_archs()
    source = CudaEmitter(module).emit().encode()
    if capability in archs:
        prog = _program(source, _options(module, f"sm_{capability}"))
        size = _check(nvrtc.nvrtcGetCUBINSize(prog), "nvrtcGetCUBINSize")
        cubin = b" " * size
        _check((nvrtc.nvrtcGetCUBIN(prog, cubin)[0], None), "nvrtcGetCUBIN")
        return bytes(cubin)
    usable = [a for a in archs if a <= capability] or archs[:1]
    return bytes(compile_ptx(module, f"compute_{max(usable)}").encode()) + b"\0"


def compiled_image(module: ir.Module, capability: int) -> bytes:
    """The loadable image for a module, cached on disk: NVRTC takes seconds to tens of seconds for the render
    kernel, so only the first run on a machine (or after a kernel change) pays for it."""
    version = ".".join(map(str, _check(nvrtc.nvrtcVersion(), "nvrtcVersion")))
    key = hashlib.sha1(
        CudaEmitter(module).emit().encode() + f"|{capability}|{version}|{_options(module, '')}".encode()
    ).hexdigest()
    path = CACHE / f"{key}.bin"
    with contextlib.suppress(OSError):
        return path.read_bytes()
    image = _compile_image(module, capability)
    with contextlib.suppress(OSError):
        CACHE.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(f".{os.getpid()}.tmp")
        temporary.write_bytes(image)
        temporary.replace(path)  # atomic: concurrent processes never read half a file
    return image


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

    def finish(self) -> None:
        self.backend.activate()
        _check((driver.cuCtxSynchronize()[0], None), "cuCtxSynchronize")

    def read(self, name: str) -> np.ndarray:
        size, dtype = self.shapes[name]
        result = np.empty(size, dtype)
        self.backend.activate()
        if result.nbytes:
            _check((driver.cuMemcpyDtoH(result.ctypes.data, self.device[name][0], result.nbytes)[0], None), "DtoH")
        return result

    def read_range(self, name: str, start: int, stop: int) -> np.ndarray:
        _, dtype = self.shapes[name]
        result = np.empty(max(0, stop - start), dtype)
        self.backend.activate()
        if result.nbytes:
            source = driver.CUdeviceptr(int(self.device[name][0]) + start * result.itemsize)
            _check((driver.cuMemcpyDtoH(result.ctypes.data, source, result.nbytes)[0], None), "DtoH")
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
        self.capability = major * 10 + minor  # pragma: no cover
        name = _check(driver.cuDeviceGetName(128, self.device), "cuDeviceGetName")  # pragma: no cover
        self.device_name = bytes(name).split(b"\0")[0].decode()  # pragma: no cover
        self._functions: dict[tuple[int, str], tuple[ir.Module, Any]] = {}  # pragma: no cover

    def activate(self) -> None:  # pragma: no cover - needs an NVIDIA GPU
        """Make the primary context current on the calling thread (render workers run off the GUI thread)."""
        _check((driver.cuCtxSetCurrent(self.ctx)[0], None), "cuCtxSetCurrent")

    def function(self, launch: Launch) -> Any:  # pragma: no cover - needs an NVIDIA GPU
        key = (id(launch.module), launch.kernel)  # the module is kept in the entry, so its id is never reused
        entry = self._functions.get(key)
        if entry is None or entry[0] is not launch.module:
            image = compiled_image(launch.module, self.capability)
            module = _check(driver.cuModuleLoadData(image), "cuModuleLoadData")
            entry = (launch.module, _check(driver.cuModuleGetFunction(module, launch.kernel.encode()), "function"))
            self._functions[key] = entry
        return entry[1]

    def bind(self, launch: Launch) -> Bound:  # pragma: no cover - needs an NVIDIA GPU
        return CudaBound(self, launch)
