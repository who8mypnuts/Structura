"""ViewportHost: the GL viewport, switching to the CPU preview if OpenGL is unusable (docs/08 §9).

The QOpenGLWidget is only created when the GPU preview is wanted *and* the OpenGL probe (gl_probe) found a
usable context: a failing GL widget would also stop its whole window from being shown (see gl_probe).
"""

from __future__ import annotations

import logging
import os
from dataclasses import replace
from functools import cache

import numpy as np
from PySide6.QtCore import QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QStackedWidget, QWidget

from ...core.scene.camera import Camera, framed
from ...core.scene.ir import SceneIR
from ...preview.instances import PreviewScene
from ...preview.options import PreviewOptions
from ...services.render import RenderService
from . import gl_probe
from .cpu_viewport import CpuViewport
from .viewport_widget import ViewportWidget

log = logging.getLogger(__name__)
GL_START_TIMEOUT_MS = 1500


def preferred_backend() -> str:
    """'gpu', 'cpu' or 'off'. STRUCTURA_PREVIEW overrides (gpu forces the GL widget even if the probe failed);
    otherwise headless Qt platforms and systems without a usable OpenGL context get the CPU preview."""
    choice = os.environ.get("STRUCTURA_PREVIEW", "auto").lower()
    if choice in ("gpu", "cpu", "off"):
        return choice
    if QGuiApplication.platformName() in gl_probe.HEADLESS_PLATFORMS:
        return "cpu"
    return "gpu" if gpu_preview_usable() else "cpu"


@cache
def gpu_preview_usable() -> bool:
    """Probe OpenGL once and say what was found (the log is the first thing to ask for in a bug report)."""
    result = gl_probe.probe()
    if result.ok:
        log.info("OpenGL preview: %s", result.attempts[-1].detail)
    else:
        log.warning("OpenGL preview unavailable, using the CPU preview. %s. Run 'structura doctor' for details.",
                    result.summary())  # fmt: skip
    return result.ok


class ViewportHost(QStackedWidget):
    picked = Signal(object)
    camera_changed = Signal(object)
    mode_changed = Signal(str)  # "gpu" | "cpu" | "off"

    def __init__(self, renders: RenderService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.mode = preferred_backend()
        self.cpu = CpuViewport(renders)
        self.cpu.enabled = self.mode != "off"
        self.gl: ViewportWidget | None = None
        if self.mode == "gpu":
            self.gl = ViewportWidget()
            self.addWidget(self.gl)
            self.gl.gl_failed.connect(self._use_cpu)
            self.gl.picked.connect(self.picked)
            self.gl.camera_changed.connect(self.camera_changed)
        self.addWidget(self.cpu)
        self.cpu.picked.connect(self.picked)
        self.cpu.camera_changed.connect(self.camera_changed)
        self._options = PreviewOptions()
        self._watchdog = QTimer(self)  # some platforms never initialise a child QOpenGLWidget
        self._watchdog.setSingleShot(True)
        self._watchdog.setInterval(GL_START_TIMEOUT_MS)
        self._watchdog.timeout.connect(self._check_gl)
        self.scene: SceneIR | None = None
        self.preview: PreviewScene | None = None

    @property
    def cpu_mode(self) -> bool:
        return self.gl is None or self.currentWidget() is self.cpu

    def showEvent(self, event: object) -> None:  # noqa: N802
        super().showEvent(event)  # type: ignore[arg-type]
        if self.gl is not None and self.gl.renderer is None and not self.cpu_mode:
            self._watchdog.start()
        self.mode_changed.emit("cpu" if self.cpu_mode and self.mode != "off" else self.mode)

    @Slot()
    def _check_gl(self) -> None:
        if self.gl is not None and self.gl.renderer is None and not self.cpu_mode:
            self._use_cpu("the OpenGL widget was never initialised on this platform")

    @Slot(str)
    def _use_cpu(self, reason: str) -> None:
        log.warning("OpenGL preview unavailable (%s); using the CPU preview", reason)
        camera = self.camera()
        self.setCurrentWidget(self.cpu)
        self.cpu.set_scene(self.scene, camera)
        self.mode_changed.emit("cpu")

    def set_scene(self, scene: SceneIR, preview: PreviewScene, camera: Camera | None) -> None:
        self.scene, self.preview = scene, preview
        if self.gl is not None:
            self.gl.set_scene(preview, camera)
        if self.cpu_mode:
            self.cpu.set_scene(scene, camera)

    def camera(self) -> Camera:
        return self.cpu.camera() if self.cpu_mode or self.gl is None else self.gl.camera()

    def set_camera(self, camera: Camera) -> None:
        if self.gl is not None:
            self.gl.set_camera(camera)
        if self.cpu_mode:
            self.cpu.set_camera(camera)

    def frame_all(self) -> None:
        if self.preview is None:
            return
        aspect = self.width() / max(1, self.height())
        lo, hi = np.asarray(self.preview.lo), np.asarray(self.preview.hi)
        self.set_camera(framed(self.camera(), lo, hi, aspect))

    @property
    def options(self) -> PreviewOptions:
        return self._options

    def set_options(self, options: PreviewOptions) -> None:
        self._options = options
        if self.gl is not None:
            self.gl.set_options(options)

    def select(self, row: int | None) -> None:

        self.set_options(replace(self._options, selected=row))
