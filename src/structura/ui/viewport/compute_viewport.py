"""Compute preview (docs/08 §9): the precision engine's 'preview' integrator, shown as an image. Used when
OpenGL 3.3 is unavailable. It runs on the best compute device — CUDA, OpenCL or wgpu (Vulkan / Metal /
Direct3D) on a GPU, all CPU cores otherwise — so a machine without usable OpenGL still gets a GPU preview.
Lower resolution while moving, refined when idle."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QImage, QKeyEvent, QMouseEvent, QPainter, QPaintEvent, QWheelEvent
from PySide6.QtWidgets import QWidget

from ...core.scene.camera import Camera
from ...core.scene.ir import SceneIR
from ...render.api import script_settings
from ...render.output import Display
from ...render.settings import AUTO_PASSES, RenderSettings
from ...services.render import RenderRequest, RenderService, RenderUpdate
from ..i18n import tr
from .navigation import Navigator, numpad_view
from .orbit import OrbitController
from .viewport_widget import CLICK_SLOP

DOC = "viewport-cpu"
IDLE_MS = 250
DISPLAY = Display(0.0, "soft")  # made by the render job, so the GUI thread only wraps it in a QImage
RENDERED_SAMPLES = 64


class ComputeViewport(QWidget):
    """The viewport drawn by the render kernels (no OpenGL, or the Rendered view): progressive images from the
    render service, with the same navigation as the OpenGL viewport.
    """

    picked = Signal(object)
    camera_changed = Signal(object)
    device_changed = Signal(str)  # the device the preview runs on, e.g. "cuda NVIDIA GeForce GTX 1660"
    clicked = Signal(QPoint, bool)  # widget position, Alt held: the host picks on the CPU
    frame_requested = Signal(bool)  # F: frame all; Shift+F: frame the selection
    view_requested = Signal(str)  # a keypad standard view (navigation.numpad_view)
    menu_requested = Signal(QPoint)  # a right-click without a drag: the viewport menu

    def __init__(self, renders: RenderService, parent: QWidget | None = None, device: str = "auto") -> None:
        super().__init__(parent)
        self.renders = renders
        self.orbit = OrbitController()
        self.navigator = Navigator(self.orbit)
        self.scene: SceneIR | None = None
        self.enabled = True  # False: never render (tests, STRUCTURA_PREVIEW=off)
        self.rendered = False  # True: the Rendered view (path tracing) instead of the quick preview
        self.display = DISPLAY
        self.device = device  # compute.select name; "auto" = the best available (GPU first)
        self.device_label = ""
        self.image: QImage | None = None
        self._press: QPoint | None = None
        self._idle = QTimer(self)
        self._idle.setSingleShot(True)
        self._idle.setInterval(IDLE_MS)
        self._idle.timeout.connect(self._refine)
        renders.progress.connect(self._on_update)
        renders.finished.connect(self._on_update)
        self.setMinimumSize(160, 120)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # fly keys
        self.setAccessibleName(tr("Viewport"))

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
        """Preview: the quick 'preview' integrator. Rendered view: the script's own render settings, path traced
        progressively (one sample while moving, RENDERED_SAMPLES when the camera rests)."""
        scale = 0.5 if fast else 1.0
        w, h = max(8, int(self.width() * scale)), max(8, int(self.height() * scale))
        if not self.rendered or self.scene is None:
            return RenderSettings(width=w, height=h, samples=1 if fast else 4, samples_per_pass=1, integrator="preview")
        base = script_settings(self.scene)
        integrator = "classic" if base.integrator == "classic" else "path"
        samples = 1 if fast else RENDERED_SAMPLES
        return replace(base, width=w, height=h, samples=samples, samples_per_pass=AUTO_PASSES, frame=False, aovs=False,
                       integrator=integrator)  # fmt: skip

    def _request(self, fast: bool) -> None:
        """Asks for a render of the current camera (fast: half size, one sample, while moving)."""
        if not self.enabled:
            return
        if self.scene is None or len(self.scene) == 0:
            self.image = None
            self.update()
            return
        settings = self._settings(fast)
        camera = self.orbit.camera()
        self.display = settings.display if self.rendered else DISPLAY  # the script's exposure and look
        self.renders.request(RenderRequest(DOC, self.scene, settings, self.device, camera=camera, display=self.display))

    @Slot()
    def _refine(self) -> None:
        self._request(fast=False)

    @Slot(str, object)
    def _on_update(self, doc: str, update: object) -> None:
        """Shows a render pass of this viewport."""
        if doc != DOC or not isinstance(update, RenderUpdate):
            return
        rgb = update.display if update.display is not None else self.display.apply(update.progress.image)
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
        kind = "rendered" if self.rendered else "preview"
        return f"CPU {kind}" if backend in ("", "cpu") else f"{backend.upper()} {kind}"

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._press = event.position().toPoint()
        self.navigator.press(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self.navigator.move(event):
            self._moved()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        pos = event.position().toPoint()
        if self._press is not None and (pos - self._press).manhattanLength() <= CLICK_SLOP:
            if event.button() == Qt.MouseButton.RightButton:
                self.menu_requested.emit(pos)
            else:
                self.clicked.emit(pos, bool(event.modifiers() & Qt.KeyboardModifier.AltModifier))
        self._press = None
        self.navigator.release()

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        self.navigator.wheel(event.angleDelta().y() / 120.0, event.modifiers())
        self._moved()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if self.navigator.key(event):
            self._moved()
        elif (view := numpad_view(event)) is not None:
            self.view_requested.emit(view)
        elif event.key() == Qt.Key.Key_F:
            self.frame_requested.emit(bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier))
        else:
            super().keyPressEvent(event)
