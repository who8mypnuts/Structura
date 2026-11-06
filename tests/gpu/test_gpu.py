"""Hardware checks for the reference machine (GTX 1660): `pytest -m gpu` (docs/19 §4)."""

from __future__ import annotations

import pytest

from structura.compute.base import BackendUnavailableError
from structura.compute.cuda import CudaBackend
from structura.compute.select import select_backend

pytestmark = pytest.mark.gpu


def test_auto_selects_a_gpu_backend() -> None:
    backend = select_backend("auto")
    if backend.name == "cpu":
        pytest.skip("no GPU backend on this machine")
    assert backend.is_gpu


def test_cuda_device_is_usable() -> None:
    try:
        backend = CudaBackend()
    except BackendUnavailableError as exc:
        pytest.skip(str(exc))
    assert backend.arch.startswith("compute_")
