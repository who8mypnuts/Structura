"""The 3D viewport: a QOpenGLWidget hosting the preview engine (docs/08). All GL work happens in paintGL on
the GUI thread; the widget keeps repainting until accumulation AA converges, then goes idle.

The context uses the application's default QSurfaceFormat, which start-up sets from the OpenGL probe
(gl_probe), so the widget and the window's compositing context always agree."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QWidget

from ...core.scene.camera import Camera
from ...preview.instances import PreviewScene
from ...preview.options import PreviewOptions
from .orbit import OrbitController

CLICK_SLOP = 4  # pixels a press may move and still count as a click (pick)


class ViewportWidget(QOpenGLWidget):
    picked = Signal(object)  # SceneIR row or None
    gl_failed = Signal(str)  # the host switches to the CPU preview
    camera_changed = Signal(object)  # Camera

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(160, 120)
        self.orbit = OrbitController()
        self.options = PreviewOptions()
        self.renderer: Any = None
        self._scene: PreviewScene | None = None
        self._scene_dirty = False
        self._press: QPoint | None = None
        self._last: QPoint | None = None
        self._refine = QTimer(self)
        self._refine.setInterval(16)
        self._refine.timeout.connect(self.update)

    # -- public API ----------------------------------------------------------------------------------------
    def set_scene(self, scene: PreviewScene | None, camera: Camera | None = None) -> None:
        self._scene, self._scene_dirty = scene, True
        if camera is not None:
            self.orbit.set_camera(camera)
        self.update()

    def set_options(self, options: PreviewOptions) -> None:
        self.options = options
        self.update()

    def set_camera(self, camera: Camera) -> None:
        self.orbit.set_camera(camera)
        self._camera_moved()

    def camera(self) -> Camera:
        return self.orbit.camera()

    def frame_all(self) -> None:
        if self._scene is not None:
            self.orbit.frame(self._scene.lo, self._scene.hi, self.width() / max(1, self.height()))
            self._camera_moved()

    def select(self, row: int | None) -> None:
        self.set_options(replace(self.options, selected=row))

    # -- GL ------------------------------------------------------------------------------------------------
    def initializeGL(self) -> None:  # noqa: N802
        try:
            import moderngl  # noqa: PLC0415 - imported where the context exists

            from ...preview.renderer import PreviewRenderer  # noqa: PLC0415

            self.ctx = moderngl.create_context()
            self.renderer = PreviewRenderer(self.ctx)
            self._scene_dirty = True
        except Exception as exc:
            self.renderer = None
            self.gl_failed.emit(str(exc))

    def paintGL(self) -> None:  # noqa: N802
        if self.renderer is None:
            return
        if self._scene_dirty:
            self.renderer.set_scene(self._scene)
            self._scene_dirty = False
        ratio = self.devicePixelRatioF()
        size = (round(self.width() * ratio), round(self.height() * ratio))
        target = self.ctx.detect_framebuffer(self.defaultFramebufferObject())
        self.renderer.render(self.orbit.camera(), target, size, self.options)
        if self.renderer.converged:
            self._refine.stop()
        elif not self._refine.isActive():
            self._refine.start()

    # -- interaction ---------------------------------------------------------------------------------------
    def _camera_moved(self) -> None:
        self.camera_changed.emit(self.orbit.camera())
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._press = self._last = event.position().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._last is None:
            return
        pos = event.position().toPoint()
        delta = pos - self._last
        self._last = pos
        buttons, mods = event.buttons(), event.modifiers()
        if buttons & Qt.MouseButton.MiddleButton or (mods & Qt.KeyboardModifier.ShiftModifier):
            self.orbit.pan(delta.x(), delta.y())
        elif mods & Qt.KeyboardModifier.AltModifier:
            self.orbit.dolly(-delta.y() / 40.0)
            self.orbit.roll(delta.x() * 0.005)
        elif buttons & (Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton):
            self.orbit.orbit(delta.x(), delta.y())
        self._camera_moved()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        pos = event.position().toPoint()
        if self._press is not None and (pos - self._press).manhattanLength() <= CLICK_SLOP:
            self.pick_at(pos)
        self._press = self._last = None

    def pick_at(self, pos: QPoint) -> None:
        if self.renderer is None:
            return
        ratio = self.devicePixelRatioF()
        self.makeCurrent()
        row = self.renderer.pick(round(pos.x() * ratio), round(pos.y() * ratio))
        self.doneCurrent()
        self.picked.emit(row)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        self.orbit.dolly(event.angleDelta().y() / 120.0)
        self._camera_moved()

    def keyPressEvent(self, event: Any) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_F:
            self.frame_all()
        else:
            super().keyPressEvent(event)
