"""Saving renders and render reports (docs/09 §8): Save As dialogs, then the work on the io lane."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Slot, qVersion

from ..core.build.driver import BuildStats
from ..render.api import script_settings
from ..render.metadata import render_metadata
from ..render.output import save_image
from ..render.report.collect import ReportInputs, build_report
from ..render.report.writers import FORMATS, report_filters
from ..services.jobs import ErrorInfo, FunctionJob, JobContext, Lane
from ..services.report_documents import write_report
from .i18n import tr
from .render_queue import report_path
from .render_view.render_view import RenderInput
from .save_paths import SavePaths, stem_for, with_extension

if TYPE_CHECKING:
    from .app_window import MainWindow

IMAGE_FILTERS = ["PNG image (*.png)", "OpenEXR, with AOV layers (*.exr)", "JPEG image (*.jpg)", "WebP image (*.webp)",
                 "TIFF image (*.tif)"]  # fmt: skip


@dataclass(frozen=True)
class RenderContext:
    """The document a render was started from (the tab may change or close while it runs)."""

    script_path: Path | None = None
    seed: int = 0
    params: dict[str, float] = field(default_factory=dict)
    build: BuildStats | None = None


def _suffix(path: Path, filters: list[str], chosen: str, default: str) -> Path:
    """Add the chosen filter's extension when the typed name has none."""
    if path.suffix:
        return path
    extension = chosen.rsplit("*", 1)[-1].rstrip(")") if "*" in chosen else default
    return with_extension(path, (extension,))


class RenderActions(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        self.paths = SavePaths(window.settings)
        self.context = RenderContext()
        self.saved: tuple[Path, ...] = ()  # image files written for the current render (listed in reports)
        view = window.render_view
        view.started.connect(self._started)
        view.controls.save_button.clicked.connect(self.save_render)
        view.controls.report_button.clicked.connect(self.save_report)

    @Slot()
    def _started(self) -> None:
        tab = self.w.tabs.current()
        if tab is not None:
            build = tab.outcome.stats if tab.outcome is not None else None
            self.context = RenderContext(tab.path, tab.seed, dict(tab.params), build)
        self.saved = ()

    def start_render(self) -> None:
        self.w.views.setCurrentWidget(self.w.render_view)
        self.w.render_view.start()

    def render_source(self) -> RenderInput | None:
        tab = self.w.tabs.current()
        if tab is None or tab.outcome is None:
            return None
        size = self.w.render_view.controls.image_size((self.w.viewport.width(), self.w.viewport.height()))
        quick = self.w.render_view.settings(*size)
        base = script_settings(tab.outcome.scene)  # the script's legacy keys and v2 blocks …
        settings = self.w.render_settings.apply(base)  # … the panel's values …
        noise = settings.noise_threshold or quick.noise_threshold  # (the panel's threshold wins over the preset's)
        settings = replace(  # … and the toolbar
            settings, frame=False, width=quick.width, height=quick.height, samples=quick.samples,
            samples_per_pass=quick.samples_per_pass, integrator=quick.integrator, aovs=quick.aovs,
            noise_threshold=noise, asset_dir=str(tab.path.parent) if tab.path else "",
        )  # fmt: skip
        return tab.outcome.scene, self.w.viewport.camera(), settings, tab.text()

    # -- images ------------------------------------------------------------------------------------------------
    def save_render(self) -> None:
        view = self.w.render_view
        image, last, source = view.shown_image(), view.last, view.source
        if image is None or last is None or source is None:
            self.w.show_message(tr("Render first (F9), then save."))
            return
        suggestion = self.paths.suggest("render", stem_for(self.context.script_path, "render") + ".png",
                                        self.context.script_path)  # fmt: skip
        answer = self.paths.ask(self.w, "render", tr("Save Render"), suggestion, IMAGE_FILTERS, IMAGE_FILTERS[0])
        if answer is None:
            return
        path = _suffix(answer[0], IMAGE_FILTERS, answer[1], ".png")
        _, camera, settings, script = source
        meta = render_metadata(settings, camera, script, self.context.params)
        layers = last.progress.aovs.layers() if last.progress.aovs is not None else None
        exposure, view_name = view.controls.exposure.value(), view.controls.view_transform()

        def run(ctx: JobContext) -> Path:
            save_image(image, path, exposure, view_name, meta, layers)
            return path

        self._io(f"save {path.name}", run, tr("Saved {name}"))
        self.saved = (*self.saved, path)

    # -- the queue ---------------------------------------------------------------------------------------------
    def queue_render(self) -> None:
        """Render ▸ Add to Render Queue: the current view, with the tool bar's settings, into a chosen file."""
        source = self.render_source()
        tab = self.w.tabs.current()
        if source is None or tab is None:
            self.w.show_message(tr("Build the script first (F5), then queue a render."))
            return
        settings, stem = source[2], stem_for(tab.path, "render")
        suggestion = self.paths.suggest("render", f"{stem}-{settings.width}x{settings.height}.png", tab.path)
        answer = self.paths.ask(self.w, "render", tr("Queue Render As"), suggestion, IMAGE_FILTERS, IMAGE_FILTERS[0])
        if answer is None:
            return
        path = _suffix(answer[0], IMAGE_FILTERS, answer[1], ".png")
        report = report_path(path, ".pdf") if self.w.queue_panel.reports.isChecked() else None
        name = f"{stem} · {settings.width}×{settings.height} · {settings.samples} spp"
        self.w.render_queue.add(name, self.w.render_view.make_request(source), path, source[3], report)
        self.w.panels.show("Render Queue")

    # -- reports -----------------------------------------------------------------------------------------------
    def report_inputs(self) -> ReportInputs | None:
        view = self.w.render_view
        last, source = view.last, view.source
        if last is None or source is None or last.details is None:
            return None
        c = self.context
        denoised = view.controls.denoise_method() is not None and last.denoised is not None
        return ReportInputs(
            scene=source[0], progress=last.progress, details=last.details, device=last.device,
            passes=last.passes, image=view.shown_image(), denoiser=last.denoiser if denoised else "",
            exposure=view.controls.exposure.value(), view=view.controls.view_transform(), script=source[3],
            script_path=c.script_path, seed=c.seed, params=c.params, build=c.build, outputs=self.saved,
            environment={"Qt": qVersion()},
        )  # fmt: skip

    def save_report(self) -> None:
        inputs = self.report_inputs()
        if inputs is None:
            self.w.show_message(tr("Render first (F9), then save a report."))
            return
        filters = report_filters()
        stem = stem_for(self.context.script_path, "render") + "-report"
        suggestion = self.paths.suggest("report", stem + ".pdf", self.context.script_path)
        answer = self.paths.ask(self.w, "report", tr("Save Render Report"), suggestion, filters, filters[0])
        if answer is None:
            return
        path = _suffix(answer[0], filters, answer[1], ".pdf")
        if path.suffix.lower() not in FORMATS:
            path = with_extension(path, (".pdf",))

        def run(ctx: JobContext) -> Path:
            write_report(build_report(inputs), path)
            return path

        self._io(f"report {path.name}", run, tr("Report saved: {name}"))

    def _io(self, name: str, fn: Callable[[JobContext], Path], done: str) -> None:
        handle = self.w.runner.submit(FunctionJob(name, Lane.IO, fn))
        handle.finished.connect(lambda result: self.w.notify_file(done.format(name=Path(result).name), Path(result)))
        handle.failed.connect(self._failed)

    @Slot(object)
    def _failed(self, info: object) -> None:
        message = info.message if isinstance(info, ErrorInfo) else str(info)
        self.w.show_message(tr("Saving failed: {error}").format(error=message))
