"""ViewportHost: the GL viewport, or the compute preview (GPU compute or CPU) when OpenGL is unusable (docs/08 §9).

The QOpenGLWidget is only created when the GPU preview is wanted *and* the OpenGL probe (gl_probe) found a
usable context: a failing GL widget would also stop its whole window from being shown (see gl_probe).
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from dataclasses import replace
from functools import cache

import numpy as np
from PySide6.QtCore import QPoint, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QStackedWidget, QWidget

from ...core.scene.camera import Camera, framed, standard_view
from ...core.scene.ir import SceneIR
from ...preview.instances import PreviewScene
from ...preview.options import PreviewOptions
from ...services.jobs import FunctionJob, Lane
from ...services.render import RenderService
from ...services.settings import SettingsService
from . import gl_probe
from .camera_motion import CameraMotion
from .compute_viewport import ComputeViewport
from .overlay import Overlays, ViewportOverlay
from .picking import PickResult, pick_job
from .viewport_widget import ViewportWidget

log = logging.getLogger(__name__)
GL_START_TIMEOUT_MS = 1500


def preview_label(mode: str) -> str:
    """Status-bar text of a preview mode: 'gpu' is OpenGL; the compute preview reports its device."""
    return {"gpu": "OpenGL", "cpu": "CPU", "off": "off", "rendered": "Rendered (path tracing)"}.get(mode, mode.upper())


def preview_device() -> str:
    """The compute device of the fallback preview: STRUCTURA_PREVIEW_DEVICE, else the best available."""
    return os.environ.get("STRUCTURA_PREVIEW_DEVICE", "auto")


BACKEND_KEY = "viewport/backend"  # Preferences ▸ Viewport ▸ Viewport engine: auto | gpu | cpu


def apply_backend_preference(settings: SettingsService) -> None:
    """Before the QApplication exists: Preferences ▸ Viewport engine becomes STRUCTURA_PREVIEW.

    The environment wins when it sets STRUCTURA_PREVIEW already.

    Args:
        settings: The preferences ('gpu' forces the OpenGL viewport even when the check fails; 'cpu' the compute
            viewport).
    """
    choice = str(settings.value(BACKEND_KEY, "auto")).lower()
    if choice in ("gpu", "cpu") and "STRUCTURA_PREVIEW" not in os.environ:
        os.environ["STRUCTURA_PREVIEW"] = choice


def preferred_backend() -> str:
    """'gpu', 'cpu' or 'off'. STRUCTURA_PREVIEW overrides (gpu forces the GL widget even if the probe failed);
    otherwise headless Qt platforms and systems without a usable OpenGL context get the compute preview."""
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
        log.warning("OpenGL preview unavailable, using the compute preview. %s. Run 'structura doctor' for details.",
                    result.summary())  # fmt: skip
    return result.ok


class ViewportHost(QStackedWidget):
    """The viewport: the OpenGL widget when the start-up check allows it, else (and for the Rendered view) the
    compute viewport; the overlays on top; picking, framing, standard views and camera moves.
    """

    picked = Signal(object)
    camera_changed = Signal(object)
    mode_changed = Signal(str)  # "gpu" | "cpu" | "off"
    menu_requested = Signal(QPoint)  # a right-click in either viewport (widget position): the viewport menu

    def __init__(self, renders: RenderService, parent: QWidget | None = None) -> None:
        """Creates the viewports the mode allows and the overlay.

        Args:
            renders: The render service (the compute viewport and the Rendered view render through it).
            parent: The parent widget.
        """
        super().__init__(parent)
        self.mode = preferred_backend()
        self.compute = ComputeViewport(renders, device=preview_device())
        self.compute.enabled = self.mode != "off"
        self.gl: ViewportWidget | None = None
        if self.mode == "gpu":
            self.gl = ViewportWidget()
            self.addWidget(self.gl)
            self.gl.gl_failed.connect(self._use_compute)
            self.gl.picked.connect(self.picked)
            self.gl.camera_changed.connect(self.camera_changed)
            self.gl.clicked.connect(self._clicked)
            self.gl.frame_requested.connect(self._frame)
            self.gl.view_requested.connect(self.standard_view)
            self.gl.menu_requested.connect(self.menu_requested)
        self.addWidget(self.compute)
        self.compute.picked.connect(self.picked)
        self.compute.camera_changed.connect(self.camera_changed)
        self.compute.clicked.connect(self._clicked)
        self.compute.frame_requested.connect(self._frame)
        self.compute.view_requested.connect(self.standard_view)
        self.compute.menu_requested.connect(self.menu_requested)
        self.compute.device_changed.connect(self._compute_device)
        self._options = PreviewOptions()
        self._watchdog = QTimer(self)  # some platforms never initialise a child QOpenGLWidget
        self._watchdog.setSingleShot(True)
        self._watchdog.setInterval(GL_START_TIMEOUT_MS)
        self._watchdog.timeout.connect(self._check_gl)
        self.scene: SceneIR | None = None
        self.preview: PreviewScene | None = None
        self.overlay = ViewportOverlay(self)
        self.animate_moves: Callable[[], bool] = lambda: True  # the window: False with "Reduce motion"
        self.motion = CameraMotion(self.set_camera, self._animated, self)
        self.camera_changed.connect(self.overlay.set_camera)
        if self.gl is not None:
            # Every GL frame re-composites the window; a QPainter overlay that is not repainted with it
            # vanishes while the view refines (the accumulation frames after a change).
            self.gl.frameSwapped.connect(self.overlay.update)

    def set_rendered(self, on: bool) -> None:
        """The Rendered view: the viewport path-traces the script's render settings progressively (the compute
        viewport with the 'path' integrator); off returns to the preview engine."""
        camera = self.camera()
        self.compute.rendered = on
        if self.gl is not None:
            self.setCurrentWidget(self.compute if on else self.gl)
            if not on:
                self.gl.set_camera(camera)
        if self.compute_mode and self.mode != "off":
            self.compute.set_scene(self.scene, camera)
        self.mode_changed.emit("rendered" if on else ("cpu" if self.compute_mode else self.mode))

    @property
    def rendered(self) -> bool:
        return self.compute.rendered

    @Slot(str)
    def standard_view(self, name: str) -> None:
        """Look at the structure from a side (keypad 1/3/7/5, the Camera panel, View ▸ Standard Views)."""
        bounds = self.bounds()
        if bounds is not None:
            aspect = self.width() / max(1, self.height())
            self.move_camera(standard_view(name, *bounds, aspect, self.camera().fov_y_deg))

    @Slot(bool)
    def _frame(self, selection: bool) -> None:
        (self.frame_selection if selection else self.frame_all)()

    @Slot(QPoint, bool)
    def _clicked(self, pos: QPoint, alt: bool) -> None:
        """A click the widget could not resolve itself: exact CPU picking on the compute lane. Alt+click moves
        the camera's focus (depth of field) to the clicked surface; a plain click in the compute preview picks."""
        if self.scene is None:
            return
        job = pick_job(self.scene, self.camera(), (self.width(), self.height()), pos.x(), pos.y(), alt)
        handle = self.compute.renders.runner.submit(FunctionJob("viewport pick", Lane.COMPUTE, job, key="pick"))
        handle.finished.connect(self._picked_cpu)

    @Slot(object)
    def _picked_cpu(self, result: PickResult) -> None:
        if result.focus:
            if result.distance is not None:
                self.set_camera(self.camera().focused_at(result.distance))
        else:
            self.picked.emit(result.row)

    def resizeEvent(self, event: object) -> None:  # noqa: N802
        super().resizeEvent(event)  # type: ignore[arg-type]
        self.overlay.setGeometry(self.rect())
        self.overlay.raise_()

    def set_navigation(self, preset: str) -> None:
        """Mouse and keyboard controls: 'structura', 'legacy' (Structure Synth 1.5, trackball orbit) or 'blender'."""
        for widget in (self.gl, self.compute):
            if widget is not None:
                widget.navigator.preset = preset
                widget.orbit.trackball = preset == "legacy"  # Structure Synth rotated about the view axes

    def set_orbit_lock(self, lock: str) -> None:
        """Sets the orbit lock of both viewports.

        Args:
            lock: 'free', 'horizontal' (turn around the structure only) or 'vertical'.
        """
        for widget in (self.gl, self.compute):
            if widget is not None:
                widget.navigator.lock = lock

    @property
    def orbit_lock(self) -> str:
        return self.compute.navigator.lock

    def set_overlays(self, overlays: Overlays, grid: bool) -> None:
        """Axis gizmo, bounds and HUD (both viewports); the ground grid (the GPU viewport draws it)."""
        self.overlay.options = overlays
        self.overlay.update()
        self.set_options(replace(self._options, grid=grid))

    @property
    def compute_mode(self) -> bool:
        return self.gl is None or self.currentWidget() is self.compute

    def showEvent(self, event: object) -> None:  # noqa: N802
        super().showEvent(event)  # type: ignore[arg-type]
        if self.gl is not None and self.gl.renderer is None and not self.compute_mode:
            self._watchdog.start()
        self.mode_changed.emit("cpu" if self.compute_mode and self.mode != "off" else self.mode)

    @Slot()
    def _check_gl(self) -> None:
        if self.gl is not None and self.gl.renderer is None and not self.compute_mode:
            self._use_compute("the OpenGL widget was never initialised on this platform")

    @Slot(str)
    def _compute_device(self, device: str) -> None:
        if self.compute_mode and self.mode != "off":
            self.mode_changed.emit(self.compute.badge_text().removesuffix(" preview").lower())

    @Slot(str)
    def _use_compute(self, reason: str) -> None:
        log.warning("OpenGL preview unavailable (%s); using the compute preview", reason)
        camera = self.camera()
        self.setCurrentWidget(self.compute)
        self.compute.set_scene(self.scene, camera)
        self.mode_changed.emit("cpu")

    def set_scene(self, scene: SceneIR, preview: PreviewScene, camera: Camera | None) -> None:
        self.scene, self.preview = scene, preview
        if self.gl is not None:
            self.gl.set_scene(preview, camera)
        if self.compute_mode:
            self.compute.set_scene(scene, camera)
        if camera is not None:
            self.camera_changed.emit(camera)
        counts = scene.kind_counts()
        hud = f"{len(scene):,} objects" + "".join(f" · {n:,} {k}" for k, n in list(counts.items())[:3])
        self.overlay.show_state(self.camera(), (np.asarray(preview.lo), np.asarray(preview.hi)), hud)

    def camera(self) -> Camera:
        return self.compute.camera() if self.compute_mode or self.gl is None else self.gl.camera()

    def set_camera(self, camera: Camera) -> None:
        if self.gl is not None:
            self.gl.set_camera(camera)
        if self.compute_mode:
            self.compute.set_camera(camera)
        self.camera_changed.emit(self.camera())

    def bounds(self) -> tuple[np.ndarray, np.ndarray] | None:
        """The built structure's bounding box (None before the first build)."""
        if self.preview is None:
            return None
        return np.asarray(self.preview.lo), np.asarray(self.preview.hi)

    def _animated(self) -> bool:
        return self.animate_moves()  # looked up on each move: the window replaces the predicate

    def move_camera(self, camera: Camera) -> None:
        """Glide to ``camera`` (standard views, framing, saved views)."""
        self.motion.move(self.camera(), camera)

    def selected_row(self) -> int | None:
        """Returns the SceneIR row of the clicked object, or None when nothing is selected."""
        row = self._options.selected
        return row if self.scene is not None and row is not None and 0 <= row < len(self.scene) else None

    def frame_selection(self) -> None:
        """Frame the selected (clicked) object; everything when nothing is selected."""
        row = self._options.selected
        if self.scene is None or row is None or not 0 <= row < len(self.scene):
            self.frame_all()
            return
        linear, origin = self.scene.xform[row][:, :3], self.scene.xform[row][:, 3]
        lo = origin + np.minimum(linear, 0.0).sum(axis=1)
        hi = origin + np.maximum(linear, 0.0).sum(axis=1)
        self.move_camera(framed(self.camera(), lo, hi, self.width() / max(1, self.height()), margin=2.5))

    def frame_all(self) -> None:
        if self.preview is None:
            return
        aspect = self.width() / max(1, self.height())
        lo, hi = np.asarray(self.preview.lo), np.asarray(self.preview.hi)
        self.move_camera(framed(self.camera(), lo, hi, aspect))

    @property
    def options(self) -> PreviewOptions:
        return self._options

    def highlight(self, rows: np.ndarray | None, count: int) -> None:
        """Tint these SceneIR rows (provenance hover); the GPU preview only."""
        if self.gl is not None and not self.compute_mode:
            self.gl.set_highlight(rows, count)

    def set_options(self, options: PreviewOptions) -> None:
        self._options = options
        if self.gl is not None:
            self.gl.set_options(options)

    def select(self, row: int | None) -> None:
        self.set_options(replace(self._options, selected=row))
        inside = self.scene is not None and row is not None and 0 <= row < len(self.scene)
        outline = self.compute_mode and inside  # the GPU viewport outlines the selection itself
        self.overlay.set_selected(self.scene.xform[row] if outline else None)  # type: ignore[union-attr]
