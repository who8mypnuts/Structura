"""Render view: progressive precision-engine renders of the viewport camera (docs/09 §9, docs/14 §5.4)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import numpy as np
from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import QImage
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...compute.select import NAMES
from ...core.scene.camera import Camera
from ...core.scene.ir import SceneIR
from ...render.metadata import render_metadata
from ...render.output import save_image, to_display
from ...render.settings import INTEGRATORS, RenderSettings
from ...services.jobs import ErrorInfo
from ...services.render import RenderRequest, RenderService, RenderUpdate
from .image_view import ImageView

DOC = "render-view"


class RenderView(QWidget):
    status = Signal(str)

    def __init__(self, renders: RenderService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.renders = renders
        self.view = ImageView()
        self.integrator, self.device = QComboBox(), QComboBox()
        self.integrator.addItems(sorted(INTEGRATORS))
        self.integrator.setCurrentText("path")
        self.device.addItems(list(NAMES))
        self.samples = QSpinBox()
        self.samples.setRange(1, 65536)
        self.samples.setValue(128)
        self.samples.setPrefix("spp ")
        self.progress, self.info = QProgressBar(), QLabel("")
        self.info.setObjectName("Muted")
        self.progress.setMinimumWidth(60)
        # status text changes while rendering: it is clipped rather than allowed to widen the window
        self.info.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.info.setMinimumWidth(80)
        self.render_button, self.stop_button, self.save_button = (
            QPushButton("Render"),
            QPushButton("Stop"),
            QPushButton("Save…"),
        )
        self.render_button.setProperty("accent", True)
        self._layout()
        self.last: RenderUpdate | None = None
        self.request_source: Callable[[], tuple[SceneIR, Camera, RenderSettings, str] | None] | None = None
        self.render_button.clicked.connect(self.start)
        self.stop_button.clicked.connect(self.stop)
        self.save_button.clicked.connect(self.save_dialog)
        renders.progress.connect(self._on_update)
        renders.finished.connect(self._on_update)
        renders.failed.connect(self._on_failed)

    def _layout(self) -> None:
        bar = QHBoxLayout()
        bar.setContentsMargins(8, 6, 8, 6)
        for widget in (self.integrator, self.samples, self.device, self.render_button, self.stop_button,
                       self.save_button):  # fmt: skip
            bar.addWidget(widget)
        bar.addWidget(self.progress, 1)
        bar.addWidget(self.info)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(bar)
        layout.addWidget(self.view, 1)

    def settings(self, width: int, height: int) -> RenderSettings:
        n = self.samples.value()
        return RenderSettings(
            width=width, height=height, samples=n, samples_per_pass=max(1, min(8, n // 16 or 1)),
            integrator=self.integrator.currentText(),
        )  # fmt: skip

    @Slot()
    def start(self) -> None:
        source = self.request_source() if self.request_source else None
        if source is None:
            self.status.emit("Nothing to render yet: build the script first (F5).")
            return
        scene, camera, settings, script = source
        self._script = script
        self.progress.setValue(0)
        self.renders.request(RenderRequest(DOC, scene, settings, self.device.currentText(), camera))

    @Slot()
    def stop(self) -> None:
        self.renders.cancel(DOC)

    @Slot(str, object)
    def _on_update(self, doc: str, update: object) -> None:
        if doc != DOC or not isinstance(update, RenderUpdate):
            return
        self.last = update
        rgb = np.ascontiguousarray(to_display(update.progress.image, 0.0, self._view_transform()))
        h, w, _ = rgb.shape
        self.view.set_image(QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy())
        self.progress.setValue(round(100 * update.fraction))
        p = update.progress
        self.info.setText(f"{p.samples}/{update.total_samples} spp · {p.seconds:.1f} s · {update.device}")
        self.info.setToolTip(self.info.text())

    def _view_transform(self) -> str:
        return "standard" if self.integrator.currentText() == "classic" else "soft"

    @Slot(str, object)
    def _on_failed(self, doc: str, info: object) -> None:
        if doc == DOC and isinstance(info, ErrorInfo):
            self.info.setText("Render failed")
            self.status.emit(info.message)

    def save(self, path: Path, camera: Camera, settings: RenderSettings) -> None:
        if self.last is None:
            return
        meta = render_metadata(settings, camera, getattr(self, "_script", None))
        save_image(self.last.progress.image, path, 0.0, self._view_transform(), meta)

    @Slot()
    def save_dialog(self) -> None:
        if self.last is None:
            return
        name, _ = QFileDialog.getSaveFileName(
            self, "Save render", "render.png", "Images (*.png *.jpg *.webp *.tif *.exr)"
        )
        if name and self.request_source is not None:
            source = self.request_source()
            if source is not None:
                self.save(Path(name), source[1], source[2])
                self.status.emit(f"Saved {name}")
