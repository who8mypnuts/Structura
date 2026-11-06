"""Open Image Denoise (Intel, Apache-2.0) through its C API with ctypes (docs/03: bundled shared library).

The library is found in this order: the STRUCTURA_OIDN environment variable (a file or a folder), the
bundled copy under structura/resources/oidn/, then the system library path. OIDN 2.x and 1.x are supported
(the boolean setter was renamed in 2.0).
"""

from __future__ import annotations

import ctypes
import ctypes.util
import os
import sys
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import numpy as np

BUNDLED = Path(__file__).resolve().parents[2] / "resources" / "oidn"
NAMES = {"linux": ("libOpenImageDenoise.so.2", "libOpenImageDenoise.so"),
         "darwin": ("libOpenImageDenoise.2.dylib", "libOpenImageDenoise.dylib"),
         "win32": ("OpenImageDenoise.dll",)}  # fmt: skip
FORMAT_FLOAT3 = 3
DEVICE_DEFAULT = 0


class OidnUnavailableError(RuntimeError):
    pass


def _candidates() -> list[str]:
    names = NAMES.get(sys.platform, NAMES["linux"])
    found: list[str] = []
    override = os.environ.get("STRUCTURA_OIDN", "")
    if override:
        path = Path(override)
        found += [str(path)] if path.is_file() else [str(path / n) for n in names]
    found += [str(BUNDLED / n) for n in names if (BUNDLED / n).exists()]
    system = ctypes.util.find_library("OpenImageDenoise")
    return [*found, *([system] if system else []), *names]


@dataclass(frozen=True)
class Oidn:
    lib: ctypes.CDLL
    set_bool: Any  # oidnSetFilterBool (2.x) or oidnSetFilter1b (1.x)


@cache
def library() -> Oidn:
    for candidate in _candidates():
        try:
            lib = ctypes.CDLL(candidate)
        except OSError:
            continue
        return _declare(lib)
    raise OidnUnavailableError("libOpenImageDenoise not found (set STRUCTURA_OIDN to its path)")


def _declare(lib: ctypes.CDLL) -> Oidn:
    vp, cp, sz = ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t
    signatures = {
        "oidnNewDevice": ([ctypes.c_int], vp), "oidnCommitDevice": ([vp], None),
        "oidnGetDeviceError": ([vp, ctypes.POINTER(cp)], ctypes.c_int), "oidnReleaseDevice": ([vp], None),
        "oidnNewFilter": ([vp, cp], vp), "oidnCommitFilter": ([vp], None), "oidnExecuteFilter": ([vp], None),
        "oidnReleaseFilter": ([vp], None),
        "oidnSetSharedFilterImage": ([vp, cp, vp, ctypes.c_int, sz, sz, sz, sz, sz], None),
    }  # fmt: skip
    for name, (args, result) in signatures.items():
        function = getattr(lib, name)
        function.argtypes, function.restype = args, result
    setter = getattr(lib, "oidnSetFilterBool", None) or lib.oidnSetFilter1b  # 2.x, else 1.x
    setter.argtypes, setter.restype = [vp, cp, ctypes.c_bool], None
    return Oidn(lib, setter)


def _check(lib: ctypes.CDLL, device: int) -> None:
    message = ctypes.c_char_p()
    if lib.oidnGetDeviceError(device, ctypes.byref(message)):
        raise RuntimeError(f"Open Image Denoise: {(message.value or b'error').decode()}")


def _image(lib: ctypes.CDLL, flt: int, name: str, array: np.ndarray) -> None:
    h, w, _ = array.shape
    lib.oidnSetSharedFilterImage(flt, name.encode(), array.ctypes.data, FORMAT_FLOAT3, w, h, 0, 0, 0)


def oidn_denoise(image: np.ndarray, albedo: np.ndarray | None = None, normal: np.ndarray | None = None) -> np.ndarray:
    """Denoise an HDR image with the 'RT' filter (albedo / normal improve detail when given)."""
    oidn = library()
    lib = oidn.lib
    color = np.ascontiguousarray(image, np.float32)
    output = np.empty_like(color)
    aux = [("albedo", albedo), ("normal", normal)]
    kept = [(n, np.ascontiguousarray(a, np.float32)) for n, a in aux if a is not None]  # alive until executed
    device = lib.oidnNewDevice(DEVICE_DEFAULT)
    try:
        lib.oidnCommitDevice(device)
        _check(lib, device)
        flt = lib.oidnNewFilter(device, b"RT")
        _image(lib, flt, "color", color)
        _image(lib, flt, "output", output)
        for name, array in kept:
            _image(lib, flt, name, array)
        oidn.set_bool(flt, b"hdr", True)
        lib.oidnCommitFilter(flt)
        lib.oidnExecuteFilter(flt)
        _check(lib, device)
        lib.oidnReleaseFilter(flt)
    finally:
        lib.oidnReleaseDevice(device)
    return output
