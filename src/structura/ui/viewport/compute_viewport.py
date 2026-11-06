"""Compute preview (docs/08 §9): the precision engine's 'preview' integrator, shown as an image. Used when
OpenGL 3.3 is unavailable. It runs on the best compute device — CUDA, OpenCL or wgpu (Vulkan / Metal /
Direct3D) on a GPU, all CPU cores otherwise — so a machine without usable OpenGL still gets a GPU preview.
Lower resolution while moving, refined when idle."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPaintEvent, QWheelEvent
from PySide6.QtWidgets import QWidget

from ...core.scene.camera import Camera
from ...core.scene.ir import SceneIR
from ...render.output import to_display
from ...render.settings import RenderSettings
from ...services.render import RenderRequest, RenderService, RenderUpdate
from .orbit import OrbitController

DOC = "viewport-cpu"
IDLE_MS = 250
DISPLAY = (0.0, "soft")  # made by the render job, so the GUI thread only wraps it in a QImage


class ComputeViewport(QWidget):
    picked = Signal(object)
    camera_changed = Signal(object)
    device_changed = Signal(str)  # the device the preview runs on, e.g. "cuda NVIDIA GeForce GTX 1660"

    def __init__(self, renders: RenderService, parent: QWidget | None = None, device: str = "auto") -> None:
        super().__init__(parent)
        self.renders = renders
        self.orbit = OrbitController()
        self.scene: SceneIR | None = None
        self.enabled = True  # False: never render (tests, STRUCTURA_PREVIEW=off)
        self.device = device  # compute.select name; "auto" = the best available (GPU first)
        self.device_label = ""
        self.image: QImage | None = None
        self._last: QPoint | None = None
        self._idle = QTimer(self)
        self._idle.setSingleShot(True)
        self._idle.setInterval(IDLE_MS)
        self._idle.timeout.connect(self._refine)
        renders.progress.connect(self._on_update)
        renders.finished.connect(self._on_update)
        self.setMinimumSize(160, 120)

    def set_scene(self, scene: SceneIR | None, camera: Camera | None = None) -> None:
        self.scene = scene
        if camera is not None:
            self.orbit.set_camera(camera)
        self._request(fast=False)

    def set_camera(self, camera: Camera) -> None:
        self.orbit.set_camera(camera)
        self._moved()

    def camera(self) -> Camera:
        return self.orbit.camera()

    def _settings(self, fast: bool) -> RenderSettings:
        scale = 0.5 if fast else 1.0
        w, h = max(8, int(self.width() * scale)), max(8, int(self.height() * scale))
        return RenderSettings(width=w, height=h, samples=1 if fast else 4, samples_per_pass=1, integrator="preview")

    def _request(self, fast: bool) -> None:
        if not self.enabled:
            return
        if self.scene is None or len(self.scene) == 0:
            self.image = None
            self.update()
            return
        settings = self._settings(fast)
        camera = self.orbit.camera()
        self.renders.request(RenderRequest(DOC, self.scene, settings, self.device, camera=camera, display=DISPLAY))

    @Slot()
    def _refine(self) -> None:
        self._request(fast=False)

    @Slot(str, object)
    def _on_update(self, doc: str, update: object) -> None:
        if doc != DOC or not isinstance(update, RenderUpdate):
            return
        rgb = update.display if update.display is not None else to_display(update.progress.image, *DISPLAY)
        rgb = np.ascontiguousarray(rgb)
        h, w, _ = rgb.shape
        self.image = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()
        if update.device != self.device_label:
            self.device_label = update.device
            self.device_changed.emit(update.device)
        self.update()

    def _moved(self) -> None:
        self.camera_changed.emit(self.orbit.camera())
        self._request(fast=True)
        self._idle.start()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().window())
        if self.image is not None:
            painter.drawImage(self.rect(), self.image)
        text = self.badge_text()
        badge = QRect(8, 8, self.fontMetrics().horizontalAdvance(text) + 24, 22)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 140))
        painter.drawRoundedRect(badge, 11, 11)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, text)

    def badge_text(self) -> str:
        backend = self.device_label.split(" ")[0] if self.device_label else ""
        return "CPU preview" if backend in ("", "cpu") else f"{backend.upper()} preview"

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._last = event.position().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._last is None:
            return
        pos = event.position().toPoint()
        d, self._last = pos - self._last, pos
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier or event.buttons() & Qt.MouseButton.MiddleButton:
            self.orbit.pan(d.x(), d.y())
        else:
            self.orbit.orbit(d.x(), d.y())
        self._moved()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._last = None

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        self.orbit.dolly(event.angleDelta().y() / 120.0)
        self._moved()
