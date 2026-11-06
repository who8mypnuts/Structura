"""Render view: progressive precision-engine renders of the viewport camera (docs/09 §9, docs/14 §5.4)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import numpy as np
from PySide6.QtCore import QRect, Signal, Slot
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QFileDialog, QVBoxLayout, QWidget

from ...core.scene.camera import Camera
from ...core.scene.ir import SceneIR
from ...render.aov_display import channel_preview
from ...render.api import RenderProgress
from ...render.metadata import render_metadata
from ...render.output import save_image, to_display
from ...render.settings import RenderSettings
from ...services.jobs import ErrorInfo
from ...services.render import RenderRequest, RenderService, RenderUpdate
from .controls import RenderControls
from .image_view import ImageView
from .regions import eta, merge_base, merged

DOC = "render-view"
RenderSource = Callable[[], tuple[SceneIR, Camera, RenderSettings, str] | None]


class RenderView(QWidget):
    status = Signal(str)

    def __init__(self, renders: RenderService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.renders = renders
        self.view = ImageView()
        self.controls = c = RenderControls()
        self.integrator, self.device, self.samples, self.exposure = c.integrator, c.device, c.samples, c.exposure
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(c.tool_bar())
        layout.addWidget(self.view, 1)
        self.last: RenderUpdate | None = None
        self._base: RenderUpdate | None = None  # region renders are pasted into this result
        self.request_source: RenderSource | None = None
        self._connect()

    def _connect(self) -> None:
        c = self.controls
        c.render_button.clicked.connect(self.start)
        c.stop_button.clicked.connect(self.stop)
        c.save_button.clicked.connect(self.save_dialog)
        c.exposure.valueChanged.connect(self._redisplay)
        c.view_box.currentTextChanged.connect(self._redisplay)
        c.channel.currentTextChanged.connect(self._redisplay)
        c.denoise.currentTextChanged.connect(self._denoise_changed)
        self.renders.progress.connect(self._on_update)
        self.renders.finished.connect(self._on_update)
        self.renders.failed.connect(self._on_failed)
        self.view.region_selected.connect(self.render_region)
        self.view.hovered.connect(self.inspect)
        c.snapshot_button.clicked.connect(self.toggle_snapshot)

    def settings(self, width: int, height: int) -> RenderSettings:
        return self.controls.settings(width, height)

    @Slot()
    def start(self, region: tuple[int, int, int, int] | None = None) -> None:
        source = self.request_source() if self.request_source else None
        if source is None:
            self.status.emit("Nothing to render yet: build the script first (F5).")
            return
        scene, camera, settings, script = source
        self._script = script
        self._base = merge_base(self.last, settings, region)
        settings = replace(settings, region=region if self._base is not None else None)
        self.controls.progress.setValue(0)
        device, denoise = self.controls.device.currentText(), self.controls.denoise_method()
        display = (self.controls.exposure.value(), self.controls.view_transform())
        self.renders.request(RenderRequest(DOC, scene, settings, device, camera, denoise=denoise, display=display))

    @Slot(QRect)
    def render_region(self, rect: QRect) -> None:
        """Shift+drag in the image: render that rectangle again, keeping the rest of the last image."""
        self.start((rect.left(), rect.top(), rect.right() + 1, rect.bottom() + 1))

    @Slot()
    def toggle_snapshot(self) -> None:
        """A/B compare: keep the current image on the left of a movable split (click again to clear)."""
        image = self.view.image
        self.view.snapshot = None if self.view.snapshot is not None or image is None else image.copy()
        self.view.update()

    @Slot(int, int)
    def inspect(self, x: int, y: int) -> None:
        """Pixel inspector: the linear (HDR) value under the cursor."""
        image = self.shown_image()
        inside = image is not None and 0 <= y < image.shape[0] and 0 <= x < image.shape[1]
        text = "" if not inside else "{} {}: {:.4g} {:.4g} {:.4g}".format(x, y, *image[y, x])  # type: ignore[index]
        self.controls.pixel.setText(text)

    @Slot()
    def stop(self) -> None:
        self.renders.cancel(DOC)

    @Slot(str, object)
    def _on_update(self, doc: str, update: object) -> None:
        if doc != DOC or not isinstance(update, RenderUpdate):
            return
        self.last = merged(self._base, update)
        self._redisplay()
        self.controls.progress.setValue(round(100 * update.fraction))
        p = update.progress
        text = f"{p.samples}/{update.total_samples} spp · {p.seconds:.1f} s{eta(update)} · {update.device}"
        if 0.0 < p.active < 1.0:
            text += f" · {p.active:.0%} still sampling"
        if update.denoiser:
            text += f" · denoised ({update.denoiser})"
        self.controls.info.setText(text)
        self.controls.info.setToolTip(text)

    def show_image(self, image: np.ndarray, text: str) -> None:
        """Show an image rendered elsewhere (animation frames) with the current exposure and view."""
        self.last = RenderUpdate(RenderProgress(image, 0, 0.0), "animation", 1)
        self._redisplay()
        self.controls.info.setText(text)
        self.controls.info.setToolTip(text)

    @Slot()
    def _denoise_changed(self) -> None:
        """Denoise a finished render after the fact (on the compute lane); 'off' shows the raw image again."""
        method, last = self.controls.denoise_method(), self.last
        if method and last is not None and last.fraction >= 1.0:
            stale = last.denoised is None or method not in {"auto", last.denoiser}
            if stale:
                self.renders.denoise(DOC, last, method)
        self._redisplay()

    def shown_image(self) -> np.ndarray | None:
        """The beauty image as displayed: denoised when denoising is on and a result exists."""
        if self.last is None:
            return None
        use_denoised = self.controls.denoise_method() is not None and self.last.denoised is not None
        return self.last.denoised if use_denoised else self.last.progress.image

    def _display_rgb(self) -> np.ndarray | None:
        c, image = self.controls, self.shown_image()
        if image is None or self.last is None:
            return None
        p = self.last.progress
        preview = channel_preview(c.channel.currentText(), p.aovs, p.sample_map)
        if preview is not None:
            return to_display(preview, 0.0, "standard")
        wanted = (c.exposure.value(), c.view_transform())
        if image is p.image and self.last.display is not None and self.last.display_for == wanted:
            return self.last.display  # made by the render job: no per-pass tone mapping on the GUI thread
        return to_display(image, *wanted)

    @Slot()
    def _redisplay(self) -> None:
        """Show the last result with the current channel, exposure and view transform (no re-render)."""
        rgb = self._display_rgb()
        if rgb is None:
            return
        rgb = np.ascontiguousarray(rgb)
        h, w, _ = rgb.shape
        self.view.set_image(QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy())

    @Slot(str, object)
    def _on_failed(self, doc: str, info: object) -> None:
        if doc == DOC and isinstance(info, ErrorInfo):
            self.controls.info.setText("Render failed")
            self.status.emit(info.message)

    def save(self, path: Path, camera: Camera, settings: RenderSettings) -> None:
        image = self.shown_image()
        if image is None or self.last is None:
            return
        meta = render_metadata(settings, camera, getattr(self, "_script", None))
        aovs = self.last.progress.aovs
        c = self.controls
        save_image(image, path, c.exposure.value(), c.view_transform(), meta, aovs.layers() if aovs else None)

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
