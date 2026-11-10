"""Render view: progressive precision-engine renders of the viewport camera (docs/09 §9, docs/14 §5.4)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

import numpy as np
from PySide6.QtCore import QRect, Signal, Slot
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QVBoxLayout, QWidget

from ...core.scene.camera import Camera
from ...core.scene.ir import SceneIR
from ...render.aov_display import channel_preview
from ...render.api import RenderProgress
from ...render.output import Display, to_display
from ...render.settings import RenderSettings
from ...services.jobs import ErrorInfo
from ...services.render import RenderRequest, RenderService, RenderUpdate
from ..i18n import tr
from .controls import RenderControls
from .image_view import ImageView
from .regions import eta, merge_base, merged

DOC = "render-view"
LARGE = 1_500_000  # pixels: a new exposure, view or look for a bigger image is tone-mapped on the compute lane
RenderInput = tuple[SceneIR, Camera, RenderSettings, str]  # scene, camera, settings, script text
RenderSource = Callable[[], RenderInput | None]


class RenderView(QWidget):
    status = Signal(str)
    started = Signal()  # a render (or region render) was requested; ``source`` holds what it renders
    render_requested = Signal()  # the Render button (the window decides: final presets ask where to save first)
    finished = Signal()  # the render (and its denoising) is complete; ``last`` holds it
    activity = Signal(str)  # "Rendering 43 %" (the status bar and the window title); "" when it ends

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
        self.source: RenderInput | None = None  # of the last render started
        self._connect()

    def _connect(self) -> None:
        c = self.controls
        c.render_button.clicked.connect(self.render_requested)
        c.stop_button.clicked.connect(self.stop)
        c.resume_button.clicked.connect(self.resume)
        c.exposure.valueChanged.connect(self._redisplay)
        c.view_box.currentTextChanged.connect(self._redisplay)
        c.look.currentTextChanged.connect(self._redisplay)
        c.channel.currentTextChanged.connect(self._redisplay)
        c.denoise.currentTextChanged.connect(self.denoise_changed)
        self.renders.phase.connect(self._on_phase)
        self.renders.progress.connect(self._on_update)
        self.renders.finished.connect(self._on_update)
        self.renders.finished.connect(self._on_finished)
        self.renders.failed.connect(self._on_failed)
        self.renders.displayed.connect(self._on_displayed)
        self.view.region_selected.connect(self.render_region)
        self.view.hovered.connect(self.inspect)
        c.snapshot_button.clicked.connect(self.toggle_snapshot)

    def settings(self, width: int, height: int) -> RenderSettings:
        return self.controls.settings(width, height)

    @Slot()
    def start(self, region: tuple[int, int, int, int] | None = None) -> None:
        if self.request_source is None:
            self.status.emit("Nothing to render yet: build the script first (F5).")
            return
        source = self.request_source()  # the provider explains a refusal itself
        if source is None:
            return
        self._base = merge_base(self.last, source[2], region)
        self.controls.resume_button.setEnabled(False)
        self._busy(tr("Preparing…"))
        self.renders.request(self.make_request(source, region if self._base is not None else None))
        self.source = source
        self.started.emit()

    def make_request(self, source: RenderInput, region: tuple[int, int, int, int] | None = None) -> RenderRequest:
        """A render of ``source`` with the tool bar's device, denoiser and display settings."""
        scene, camera, settings, _ = source
        c = self.controls
        return RenderRequest(DOC, scene, replace(settings, region=region), c.device.currentText(), camera,
                             denoise=c.denoise_method(), display=self.display(settings))  # fmt: skip

    def display(self, settings: RenderSettings | None = None) -> Display:
        """The tool bar's exposure, view transform and look (a LUT is relative to the script's folder)."""
        c, source = self.controls, settings or (self.source[2] if self.source is not None else None)
        return Display(c.exposure.value(), c.view_transform(), c.post(), source.asset_dir if source else "")

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

    def _busy(self, text: str) -> None:
        """Before the first pass: a moving bar and what is happening (packing, the BVH, compiling kernels…)."""
        self.controls.progress.setRange(0, 0)
        self.controls.info.setText(text)
        self.controls.info.setToolTip(text)
        self.activity.emit(tr("Rendering: {text}").format(text=text))

    @Slot(str, str)
    def _on_phase(self, doc: str, text: str) -> None:
        if doc == DOC:
            self._busy(text)

    @Slot()
    def stop(self) -> None:
        self.renders.cancel(DOC)
        self._idle()
        self.view.set_bucket(None)
        last = self.last
        resumable = last is not None and last.fraction < 1.0 and last.progress.film is not None
        self.controls.resume_button.setEnabled(resumable and self._base is None)  # not region renders

    @Slot()
    def resume(self) -> None:
        """Continue the stopped render: same scene, camera and settings, from the samples it had."""
        if self.source is None or self.last is None or self.last.progress.film is None or self.last.fraction >= 1:
            return
        self.controls.resume_button.setEnabled(False)
        request = replace(self.make_request(self.source), resume=self.last.progress)
        self.renders.request(request)
        self.status.emit(f"Resuming at {self.last.progress.samples} spp")

    @Slot(str, object)
    def _on_update(self, doc: str, update: object) -> None:
        if doc != DOC or not isinstance(update, RenderUpdate):
            return
        self.last = merged(self._base, update)
        self._redisplay()
        self.controls.progress.setRange(0, 100)
        self.controls.progress.setValue(round(100 * update.fraction))
        self.activity.emit(tr("Rendering {percent} %").format(percent=round(100 * update.fraction)))
        p = update.progress
        self.view.set_bucket(p.tile)
        done = (
            f"{p.completed:.0%} of the buckets"
            if p.completed is not None
            else f"{p.samples}/{update.total_samples} spp"
        )
        text = f"{done} · {p.seconds:.1f} s{eta(update)} · {update.device}"
        if 0.0 < p.active < 1.0:
            text += f" · {p.active:.0%} still sampling"
        if update.denoiser:
            text += f" · denoised ({update.denoiser})"
        self.controls.info.setText(text)
        self.controls.info.setToolTip(text)

    def show_image(self, image: np.ndarray, text: str, fraction: float | None = None) -> None:
        """Show an image rendered elsewhere (animation frames) with the current exposure and view; ``fraction``
        is how far that work is (the progress bar)."""
        self.last = RenderUpdate(RenderProgress(image, 0, 0.0), "animation", 1)
        self._redisplay()
        self.controls.info.setText(text)
        self.controls.info.setToolTip(text)
        if fraction is not None:
            self.controls.progress.setRange(0, 100)
            self.controls.progress.setValue(round(100 * fraction))
            self.activity.emit("" if fraction >= 1.0 else tr("Animation {percent} %").format(
                percent=round(100 * fraction)))  # fmt: skip

    def _idle(self) -> None:
        if self.controls.progress.maximum() == 0:
            self.controls.progress.setRange(0, 100)
        self.activity.emit("")

    @Slot()
    def denoise_changed(self) -> None:
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
        wanted = self.display()
        if self.last.display_for == wanted:  # made by the render or denoise job: no tone mapping here
            made = self.last.display if image is p.image else self.last.denoised_display
            if made is not None and (image is p.image or image is self.last.denoised):
                return made
        if image.shape[0] * image.shape[1] > LARGE:
            self.renders.redisplay(DOC, self.last, wanted)
            return None  # the current picture stays until the job has made the new one (_on_displayed)
        return wanted.apply(image)

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
    def _on_displayed(self, doc: str, update: object) -> None:
        """A redisplay() result: shown if it is still of the last render (a new pass replaces it anyway)."""
        last = self.last
        if doc == DOC and isinstance(update, RenderUpdate) and last is not None and update.progress is last.progress:
            self.last = update
            self._redisplay()

    @Slot(str, object)
    def _on_finished(self, doc: str, update: object) -> None:
        if doc == DOC and isinstance(update, RenderUpdate):
            self._idle()
            self.finished.emit()

    @Slot(str, object)
    def _on_failed(self, doc: str, info: object) -> None:
        if doc == DOC and isinstance(info, ErrorInfo):
            self._idle()
            self.controls.info.setText("Render failed")
            self.status.emit(info.message)
