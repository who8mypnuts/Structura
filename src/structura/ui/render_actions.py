"""Saving renders and render reports (docs/09 §8): where the image goes and which report is written beside it
(dialogs/render_output.py), then the work on the io lane. Final renders ask first and save themselves when
they finish."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Slot, qVersion
from PySide6.QtGui import QGuiApplication

from ..core.build.driver import BuildStats
from ..render.api import script_settings
from ..render.memory import available_bytes, guard_message, render_bytes
from ..render.metadata import render_metadata
from ..render.output import save_image
from ..render.report.collect import ReportInputs, build_report
from ..render.report.text_writers import to_markdown
from ..render.report.writers import FORMATS, report_filters
from ..render.settings import RenderSettings
from ..services.jobs import ErrorInfo, FunctionJob, JobContext, Lane
from ..services.report_documents import write_report
from .dialogs.render_output import FINAL_PRESETS, REPORT_DEFAULT, REPORT_KEY, RenderOutput, choose_output, report_beside
from .i18n import tr
from .render_view.presets import CUSTOM, FRAME_VIEWPORT, PRESETS, fitted
from .render_view.render_view import RenderInput
from .save_paths import SavePaths, stem_for, with_extension

if TYPE_CHECKING:
    from .app_window import MainWindow

KEEP_KEY = "render/keep_folder"  # Preferences ▸ Rendering ▸ Keep every render (empty: off)


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
        self._done_texts: list[str] = []  # messages of the io jobs in flight, in order (one io lane)
        self._final_next: RenderOutput | None = None  # a final render about to start
        self.pending: RenderOutput | None = None  # where the running final render is saved when it finishes
        view = window.render_view
        view.render_requested.connect(self.start_render)
        view.finished.connect(self._finished)
        view.started.connect(self._started)
        view.controls.save_button.clicked.connect(self.save_render)
        view.controls.report_button.clicked.connect(self.save_report)
        c = view.controls
        for signal in (c.frame.currentTextChanged, c.preset.currentTextChanged, c.width.valueChanged,
                       c.height.valueChanged):  # fmt: skip
            signal.connect(self.update_frame_guide)
        window.workbench.scene_ready.connect(self.update_frame_guide)

    def update_frame_guide(self, *_: object) -> None:
        """The viewport shows the render frame whenever it is not the viewport's own shape."""
        aspect = self.frame_aspect()
        label = "{} × {}".format(*self.render_size()) if aspect else ""
        self.w.viewport.overlay.set_frame(aspect, label)

    @Slot()
    def _started(self) -> None:
        tab = self.w.tabs.current()
        if tab is not None:
            build = tab.outcome.stats if tab.outcome is not None else None
            self.context = RenderContext(tab.path, tab.seed, dict(tab.params), build)
        self.saved = ()
        self.pending, self._final_next = self._final_next, None

    @Slot()
    def start_render(self) -> None:
        """Render (F9). With a final preset (Final, Print 4K) it asks where the image goes first."""
        if self.w.render_view.controls.preset.currentText() in FINAL_PRESETS:
            self.final_render()
            return
        self._start()

    def _start(self) -> None:
        self.w.views.setCurrentWidget(self.w.render_view)
        self.w.render_view.start()

    def final_render(self) -> None:
        """Render ▸ Final Render…: choose the quality, the image file and the report, render, save both."""
        if self.guarded_source() is None:
            return
        controls = self.w.render_view.controls
        current = controls.preset.currentText()
        presets = (*FINAL_PRESETS, *(p.name for p in PRESETS if p.name not in FINAL_PRESETS), CUSTOM)
        if current in (*FINAL_PRESETS, CUSTOM):  # offered first: a final preset, or the tool bar's own settings
            presets = (current, *(p for p in presets if p != current))
        out = choose_output(self.w, self.paths, self._image_suggestion(), tr("Final Render"), tr("Render"), presets)
        if out is None:
            return
        controls.preset.setCurrentText(out.preset)
        self._final_next = out if out.save else None
        self._start()

    @Slot()
    def _finished(self) -> None:
        """A render (and its denoising) finished: a final render saves its image and report now."""
        out, self.pending = self.pending, None
        last = self.w.render_view.last
        if last is None or last.fraction < 1.0:
            return
        out = out or self._kept_output()
        if out is not None:
            self.write_outputs(out)

    def _kept_output(self) -> RenderOutput | None:
        """Preferences ▸ Rendering ▸ Keep every render: where a finished render goes, with its report beside it."""
        folder = str(self.w.settings.value(KEEP_KEY, "") or "")
        if not folder:
            return None
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        image = Path(folder).expanduser() / f"{stem_for(self.context.script_path, 'render')}-{stamp}.png"
        suffix = str(self.w.settings.value(REPORT_KEY, REPORT_DEFAULT))
        return RenderOutput(image, report_beside(image, suffix))

    def copy_report(self) -> None:
        """Render ▸ Copy Report as Markdown: the last render's report, for a forum post or an issue."""
        inputs = self.report_inputs()
        if inputs is None:
            self.w.show_message(tr("Render first (F9), then copy its report."))
            return
        QGuiApplication.clipboard().setText(to_markdown(build_report(inputs)))
        self.w.show_message(tr("The render report is on the clipboard (Markdown)"))

    def render_legacy(self) -> None:
        """Render ▸ Render (Legacy Look): the 'classic' integrator, Structure Synth 1.5's raytracer look."""
        self.w.render_view.controls.integrator.setCurrentText("classic")
        self.start_render()

    def render_region(self) -> None:
        view = self.w.render_view
        if view.last is None:
            self.w.show_message(tr("Render first (F9), then pick a region to render again."))
            return
        self.w.views.setCurrentWidget(view)
        view.view.pick_region()
        self.w.show_message(tr("Drag over the image: that region renders again."))

    def denoise(self) -> None:
        """Render ▸ Denoise: denoise the finished render now (Open Image Denoise, else À-Trous)."""
        controls = self.w.render_view.controls
        if controls.denoise_method() is None:
            controls.denoise.setCurrentText("auto")  # the view denoises a finished render when this changes
        else:
            self.w.render_view.denoise_changed()

    def _view_size(self) -> tuple[int, int]:
        return max(1, self.w.viewport.width()), max(1, self.w.viewport.height())

    def render_size(self) -> tuple[int, int]:
        """The image size the Render tool bar asks for (its frame and preset) for the current script."""
        tab = self.w.tabs.current()
        script = script_settings(tab.outcome.scene) if tab is not None and tab.outcome is not None else None
        default = RenderSettings()
        declared = None if script is None or (script.width, script.height) == (default.width, default.height) \
            else (script.width, script.height)  # fmt: skip
        return self.w.render_view.controls.image_size(self._view_size(), declared)

    def frame_aspect(self) -> float | None:
        """The render frame's aspect for the viewport's guide (None: the viewport's own shape)."""
        if self.w.render_view.controls.frame.currentText() == FRAME_VIEWPORT:
            return None
        width, height = self.render_size()
        return width / height

    def render_source(self) -> RenderInput | None:
        tab = self.w.tabs.current()
        if tab is None or tab.outcome is None:
            return None
        size = self.render_size()
        quick = self.w.render_view.settings(*size)
        base = script_settings(tab.outcome.scene)  # the script's legacy keys and v2 blocks …
        settings = self.w.render_settings.apply(base)  # … the panel's values …
        noise = settings.noise_threshold or quick.noise_threshold  # (the panel's threshold wins over the preset's)
        settings = replace(  # … and the toolbar
            settings, frame=False, width=quick.width, height=quick.height, samples=quick.samples,
            samples_per_pass=quick.samples_per_pass, integrator=quick.integrator, aovs=quick.aovs,
            noise_threshold=noise, asset_dir=str(tab.path.parent) if tab.path else "", mosaic=True,
        )  # fmt: skip
        view_w, view_h = self._view_size()
        camera = fitted(self.w.viewport.camera(), size[0] / size[1], view_w / view_h)  # what the frame guide shows
        return tab.outcome.scene, camera, settings, tab.text()

    def guarded_source(self) -> RenderInput | None:
        """render_source, refused (with a message) when there is nothing built or it would not fit in memory."""
        source = self.render_source()
        if source is None:
            self.w.show_message(tr("Nothing to render yet: build the script first (F5)."))
            return None
        percent = int(self.w.settings.value("render/memory_guard", 80))
        refusal = guard_message(render_bytes(source[0], source[2]), available_bytes(), percent)
        if refusal is not None:
            self.w.show_message(refusal)
            return None
        return source

    # -- images ------------------------------------------------------------------------------------------------
    def _image_suggestion(self) -> Path:
        script = self.context.script_path if self.w.render_view.last is not None else None
        tab = self.w.tabs.current()
        script = script or (tab.path if tab is not None else None)
        return self.paths.suggest("render", stem_for(script, "render") + ".png", script)

    def save_render(self) -> None:
        """Save… (Ctrl+S in the Render view): the image, and the chosen report beside it."""
        if self.w.render_view.shown_image() is None or self.w.render_view.source is None:
            self.w.show_message(tr("Render first (F9), then save."))
            return
        out = choose_output(self.w, self.paths, self._image_suggestion(), tr("Save Render"), tr("Save"))
        if out is not None:
            self.write_outputs(out)

    def write_outputs(self, out: RenderOutput) -> None:
        """Write the shown image to ``out.image``, then the report beside it (it lists the image)."""
        self._save_image(out.image)
        if out.report is not None:
            self._write_report(out.report)

    def _save_image(self, path: Path) -> None:
        view = self.w.render_view
        image, last, source = view.shown_image(), view.last, view.source
        if image is None or last is None or source is None:
            return
        _, camera, settings, script = source
        display = view.display()
        meta = render_metadata(settings, camera, script, self.context.params, display=display)
        layers = last.progress.aovs.layers() if last.progress.aovs is not None else None

        def run(ctx: JobContext) -> Path:
            path.parent.mkdir(parents=True, exist_ok=True)
            save_image(image, path, display, meta, layers)
            return path

        self._io(f"save {path.name}", run, tr("Saved {name}"))
        self.saved = (*self.saved, path)

    # -- the queue ---------------------------------------------------------------------------------------------
    def queue_render(self) -> None:
        """Render ▸ Add to Render Queue: the current view, with the tool bar's settings, into a chosen file."""
        source = self.guarded_source()
        tab = self.w.tabs.current()
        if source is None or tab is None:
            return
        settings, stem = source[2], stem_for(tab.path, "render")
        suggestion = self.paths.suggest("render", f"{stem}-{settings.width}x{settings.height}.png", tab.path)
        out = choose_output(self.w, self.paths, suggestion, tr("Queue Render As"), tr("Add to Queue"))
        if out is None:
            return
        name = f"{stem} · {settings.width}×{settings.height} · {settings.samples} spp"
        self.w.render_queue.add(name, self.w.render_view.make_request(source), out.image, source[3], out.report)
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
            display=view.display(), script=source[3],
            script_path=c.script_path, seed=c.seed, params=c.params, build=c.build, outputs=self.saved,
            environment={"Qt": qVersion()},
        )  # fmt: skip

    def save_report(self) -> None:
        """Report…: a report on its own (beside the last saved image by default), in the chosen format."""
        if self.report_inputs() is None:
            self.w.show_message(tr("Render first (F9), then save a report."))
            return
        filters = report_filters()
        remembered = str(self.w.settings.value(REPORT_KEY, REPORT_DEFAULT)) or REPORT_DEFAULT
        selected = next((f for f in filters if f"*{remembered})" in f), filters[0])
        if self.saved:  # beside the image just saved
            suggestion = report_beside(self.saved[-1], remembered) or self.saved[-1]
        else:
            stem = stem_for(self.context.script_path, "render") + "-report"
            suggestion = self.paths.suggest("report", stem + remembered, self.context.script_path)
        answer = self.paths.ask(self.w, "report", tr("Save Render Report"), suggestion, filters, selected)
        if answer is None:
            return
        path = _suffix(answer[0], filters, answer[1], ".pdf")
        if path.suffix.lower() not in FORMATS:
            path = with_extension(path, (".pdf",))
        self.w.settings.set_value(REPORT_KEY, path.suffix.lower())
        self._write_report(path)

    def _write_report(self, path: Path) -> None:
        inputs = self.report_inputs()
        if inputs is None:
            return

        def run(ctx: JobContext) -> Path:
            path.parent.mkdir(parents=True, exist_ok=True)
            write_report(build_report(inputs), path)
            return path

        self._io(f"report {path.name}", run, tr("Report saved: {name}"))

    def _io(self, name: str, fn: Callable[[JobContext], Path], done: str) -> None:
        handle = self.w.runner.submit(FunctionJob(name, Lane.IO, fn))
        self._done_texts.append(done)
        handle.finished.connect(self._written)  # bound slots: handle signals come from the io thread
        handle.failed.connect(self._failed)

    @Slot(object)
    def _written(self, result: object) -> None:
        done = self._done_texts.pop(0) if self._done_texts else "{name}"
        path = Path(str(result))
        self.w.notify_file(done.format(name=path.name), path)

    @Slot(object)
    def _failed(self, info: object) -> None:
        if self._done_texts:
            self._done_texts.pop(0)
        message = info.message if isinstance(info, ErrorInfo) else str(info)
        self.w.show_message(tr("Saving failed: {error}").format(error=message))
