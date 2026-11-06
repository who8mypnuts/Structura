"""Structure Synth '#javascript' scripts (docs/16 §3): the BuilderHost that builds, raytraces and exports
templates for the JavaScript Builder API, and the ScriptingService that runs a script as a compute-lane Job
(the QJSEngine lives in the worker thread, so the UI stays responsive). `structura run` uses the same host.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

from PySide6.QtCore import Signal, Slot

from ..compute.base import Backend
from ..compute.select import select_backend
from ..core.build.api import build_scene
from ..core.lang.api import compile_script
from ..core.scene.ir import SceneIR
from ..export.templates.engine import TemplateExport
from ..export.templates.template_file import bundled_templates, load_template
from ..render.api import render, script_settings
from ..render.output import save_image
from ..render.settings import AUTO_PASSES
from ..scripting.js_bridge import run_javascript
from .jobs import FunctionJob, JobContext, JobHandle, Lane
from .jobs.tracked import TrackedJobs

Report = Callable[[str], None]


class BuilderHost:
    """What the JavaScript Builder object calls into (scripting.js_bridge.JsHost)."""

    def __init__(self, backend: Backend, samples: int | None = None, allow_execute: bool = False,
                 report: Report | None = None, cancelled: Callable[[], bool] | None = None) -> None:  # fmt: skip
        self.backend, self.samples, self.execute = backend, samples, allow_execute
        self.report = report or (lambda _message: None)
        self._cancelled = cancelled or (lambda: False)

    def build(self, text: str, script_dir: Path) -> SceneIR:
        return build_scene(compile_script(text, 0, None, script_dir).program).scene

    def raytrace(self, scene: Any, path: Path, width: int, height: int) -> None:
        settings = replace(script_settings(scene), integrator="classic")
        if width or height:
            w, h = width or round(height * 4 / 3), height or round(width * 3 / 4)
            settings = replace(settings, width=w, height=h)
        if self.samples:
            settings = replace(settings, samples=self.samples)
        result = render(scene, replace(settings, samples_per_pass=AUTO_PASSES), self.backend)
        save_image(result.image, path, 0.0, "standard")
        self.report(f"raytraced {path.name}")

    def render_template(self, scene: Any, template: str, path: Path) -> None:
        name = Path(template).stem
        path.write_text(TemplateExport(load_template(bundled_templates()[name])).render(scene), encoding="utf-8")
        self.report(f"exported {path.name}")

    def allow_execute(self, command: str, arguments: str) -> bool:
        if not self.execute:
            self.report(f"Builder.execute({command}) was not run: external commands are disabled")
        return self.execute

    def cancelled(self) -> bool:
        return self._cancelled()


def script_job(text: str, script_dir: Path, device: str) -> Callable[[JobContext], int]:
    def run(ctx: JobContext) -> int:
        host = BuilderHost(select_backend(device), report=lambda m: ctx.progress(0.0, m, force=True),
                           cancelled=lambda: ctx.cancelled)  # fmt: skip
        written = run_javascript(text, script_dir, host)
        ctx.check_cancelled()
        return written

    return run


class ScriptingService(TrackedJobs):
    message = Signal(str, str)  # doc id, progress text ("raytraced frame0001.png")
    finished = Signal(str, int)  # doc id, files written
    failed = Signal(str, object)  # doc id, ErrorInfo

    def run(self, doc_id: str, text: str, script_dir: Path, device: str = "auto") -> JobHandle:
        self.cancel(doc_id)
        job = FunctionJob(f"javascript {doc_id}", Lane.COMPUTE, script_job(text, script_dir, device), f"js:{doc_id}")
        handle = self.submit_for(doc_id, job)
        handle.progress.connect(self._on_progress)
        handle.finished.connect(self._on_finished)
        handle.failed.connect(self._on_failed)
        return handle

    @Slot(float, str)
    def _on_progress(self, _fraction: float, text: str) -> None:
        self.message.emit(self.sender_doc(), text)

    @Slot(object)
    def _on_finished(self, written: object) -> None:
        self.finished.emit(self.sender_doc(), int(written) if isinstance(written, int) else 0)

    @Slot(object)
    def _on_failed(self, info: object) -> None:
        self.failed.emit(self.sender_doc(), info)
