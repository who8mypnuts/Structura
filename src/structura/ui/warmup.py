"""The start-up warm-up jobs (docs/04 §6 rule 5): compile the CPU kernels on the compute lane and the render
device's kernels on the device lane while the user reads the first script, so neither the first build nor
the first render (F9) waits on Numba, NVRTC or a shader compiler."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Slot

from ..compute.cpu import CpuBackend
from ..render.warmup import device_steps, warm_up
from ..services.jobs import FunctionJob, JobContext, Lane
from ..services.render import DeviceBackends

if TYPE_CHECKING:
    from .app_window import MainWindow


def _job(ctx: JobContext) -> float:
    total = 0.0
    for step, seconds in warm_up(CpuBackend()):
        total += seconds
        ctx.progress(0.0, f"kernels: {step}")
        ctx.check_cancelled()
    return total


def _device_job(backends: DeviceBackends, device: str) -> Callable[[JobContext], float]:
    def run(ctx: JobContext) -> float:
        backend = backends.get(device)  # created on the device lane, like every render
        if not backend.is_gpu:
            return 0.0  # the CPU kernels are the compute-lane job's
        ctx.progress(0.0, f"kernels: {backend.name}")
        return sum(seconds for _, seconds in warm_up(backend, device_steps(backend)))

    return run


class WarmUp(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window

    def start(self) -> None:
        handle = self.w.runner.submit(FunctionJob("warm-up", Lane.COMPUTE, _job, key="warm-up"))
        handle.finished.connect(self._done)
        device = self.w.render_view.controls.device.currentText()
        job = _device_job(self.w.renders.backends, device)
        self.w.runner.submit(FunctionJob("warm-up device", Lane.DEVICE, job, key="warm-up device")).finished.connect(
            self._done
        )
        self.w.status.showMessage("Preparing kernels in the background…", 4000)

    @Slot(object)
    def _done(self, seconds: object) -> None:
        if isinstance(seconds, float) and seconds > 2.0:  # only worth mentioning after a real compile
            self.w.show_message(f"Kernels compiled in {seconds:.0f} s; later starts reuse them")
