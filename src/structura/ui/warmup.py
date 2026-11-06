"""The start-up warm-up job (docs/04 §6 rule 5): compiles the CPU kernels on the compute lane while the
user reads the first script, so the first build and render do not wait on Numba."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Slot

from ..compute.cpu import CpuBackend
from ..render.warmup import warm_up
from ..services.jobs import FunctionJob, JobContext, Lane

if TYPE_CHECKING:
    from .app_window import MainWindow


def _job(ctx: JobContext) -> float:
    total = 0.0
    for step, seconds in warm_up(CpuBackend()):
        total += seconds
        ctx.progress(0.0, f"kernels: {step}")
        ctx.check_cancelled()
    return total


class WarmUp(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window

    def start(self) -> None:
        handle = self.w.runner.submit(FunctionJob("warm-up", Lane.COMPUTE, _job, key="warm-up"))
        handle.finished.connect(self._done)
        self.w.status.showMessage("Preparing kernels in the background…", 4000)

    @Slot(object)
    def _done(self, seconds: object) -> None:
        if isinstance(seconds, float) and seconds > 2.0:  # only worth mentioning after a real compile
            self.w.show_message(f"Kernels compiled in {seconds:.0f} s; later starts reuse them")
