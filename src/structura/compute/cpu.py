"""CPU backend: SKL → Numba (multithreaded ``prange`` dispatch; docs/11 §5)."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from functools import cache
from pathlib import Path
from types import ModuleType

import numpy as np
import platformdirs

from ..core.jit import parallel_section
from ..kernels.skl import ir
from ..kernels.skl.emit.numba_emit import NumbaEmitter
from .base import BackendBase, Bound, Launch

CACHE = Path(platformdirs.user_cache_dir("structura")) / "skl_numba"


@cache
def _load(source: str) -> ModuleType:
    """Write emitted source to a cache file (readable tracebacks) and import it."""
    digest = hashlib.sha1(source.encode()).hexdigest()[:16]
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"skl_{digest}.py"
    if not path.exists():
        path.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(f"skl_{digest}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def numba_module(module: ir.Module) -> ModuleType:
    return _load(NumbaEmitter(module).emit())


class CpuBound(Bound):
    def __init__(self, launch: Launch) -> None:
        self.arrays: dict[str, np.ndarray] = {}
        self.entry = getattr(numba_module(launch.module), f"dispatch_{launch.kernel}")
        super().__init__(launch)

    def _upload(self, name: str, host: np.ndarray) -> None:
        self.arrays[name] = host.copy()

    def dispatch(self) -> None:
        with parallel_section():  # one parallel Numba call at a time, whatever the lane (docs/04 §6)
            self.entry(*self.grid, *self.ordered_args(self.arrays))

    def read(self, name: str) -> np.ndarray:
        return self.arrays[name].copy()

    def read_range(self, name: str, start: int, stop: int) -> np.ndarray:
        return self.arrays[name][start:stop].copy()


class CpuBackend(BackendBase):
    name = "cpu"
    device_name = "CPU (Numba)"

    def bind(self, launch: Launch) -> Bound:
        return CpuBound(launch)

    def details(self) -> dict[str, str]:
        import numba  # noqa: PLC0415 - already loaded by the kernels

        return {"Numba": numba.__version__, "Threads": str(numba.get_num_threads())}
