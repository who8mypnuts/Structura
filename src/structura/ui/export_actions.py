"""Export menu actions: Save As dialog → export sheet (destination, contents, options) → ExportService job."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import shiboken6
from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QDialog, QMessageBox

from ..core.geometry.tessellate import tessellate
from ..core.scene.ir import SceneIR
from ..export.api import EXPORTERS, template_preview
from ..export.base import Exporter, ExportReport, exporter_for
from ..export.estimate import estimate_size
from ..export.mesh.meshlab import MeshCheck, check_mesh
from ..export.templates.autosave import autosave_path, script_with_settings
from ..export.templates.run_after import expand_command, missing_variables
from ..export.templates.template_file import all_templates, load_template
from ..services.export import ExportRequest, ExportService
from ..services.jobs import ErrorInfo, FunctionJob, JobContext, Lane
from .dialogs.export_dialog import ExportDialog
from .external_apps import BLENDER, MESHLAB, ExternalApp, find_app, find_blender
from .i18n import tr
from .save_paths import SavePaths, stem_for, with_extension

if TYPE_CHECKING:
    from .app_window import MainWindow
    from .documents import EditorTab

MENU_ORDER = ("obj", "ply", "stl", "3mf", "gltf", "usd", "x3d", "vrml", "meshlab", "blender", "template", "obj-legacy")
KIND = "export"  # SavePaths kind


def file_filter(exporter: Exporter) -> str:
    return f"{exporter.title} ({' '.join('*' + e for e in exporter.extensions)})"


class ExportActions(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        self.paths = SavePaths(window.settings)
        self.service = ExportService(window.runner)
        self.service.finished.connect(self._finished)
        self.service.failed.connect(self._failed)
        self.service.progress.connect(self._progress)
        self.service.cancelled.connect(self._cancelled)
        self._last: dict[str, dict[str, object]] = {}
        self.last_format = "obj"
        self.requests: dict[Path, ExportRequest] = {}  # by target path, for 'run after' commands
        self.allowed: set[str] = set()  # 'run after' commands the user allowed this session
        self.commands: dict[Path, str] = {}  # the export sheet's own 'run after' command, by target path

    def exporters(self) -> list[Exporter]:
        """The registered exporters: the curated order first, then any others (plugins) by name."""
        rest = sorted(set(EXPORTERS) - set(MENU_ORDER))
        return [EXPORTERS[name] for name in (*MENU_ORDER, *rest) if name in EXPORTERS]

    def ask_path(self, exporter: Exporter, suggestion: Path, every_format: bool) -> tuple[Exporter, Path] | None:
        """The Save As dialog. With ``every_format`` the file-type list offers all exporters, and the chosen
        type (or a typed extension that only another format uses) decides the format."""
        filters = [file_filter(e) for e in (self.exporters() if every_format else [exporter])]
        answer = self.paths.ask(self.w, KIND, tr("Export As"), suggestion, filters, file_filter(exporter))
        if answer is None:
            return None
        path, chosen = answer
        picked = next((e for e in self.exporters() if file_filter(e) == chosen), exporter)
        by_suffix = exporter_for(path)
        if path.suffix.lower() not in picked.extensions and by_suffix is not None:
            picked = by_suffix
        return picked, with_extension(path, picked.extensions)

    def _estimate(self, scene: SceneIR, dialog: ExportDialog, options: object) -> None:
        """Export two small samples on the io lane and extrapolate (export/estimate.py)."""
        exporter, camera = dialog.exporter, self.w.viewport.camera()
        suffix = dialog.path.suffix or exporter.extensions[0]

        def run(ctx: JobContext) -> int:
            return estimate_size(scene, exporter.name, suffix, dict(options), camera)  # type: ignore[call-overload]

        handle = self.w.runner.submit(FunctionJob("export estimate", Lane.IO, run, key="export-estimate"))
        handle.finished.connect(self._estimated)

    @Slot(object)
    def _estimated(self, size: object) -> None:
        dialog = getattr(self, "estimating", None)
        if isinstance(size, int) and dialog is not None and shiboken6.isValid(dialog):
            dialog.show_estimate(size)

    def _preview(self, scene: SceneIR, options: object) -> None:
        """The template sheet's Preview tab: the first 64 KB of the output, made on the io lane."""
        camera = self.w.viewport.camera()

        def run(ctx: JobContext) -> str:
            return template_preview(scene, dict(options), camera)  # type: ignore[call-overload]

        handle = self.w.runner.submit(FunctionJob("template preview", Lane.IO, run, key="template-preview"))
        handle.finished.connect(self._previewed)

    @Slot(object)
    def _previewed(self, text: object) -> None:
        dialog = getattr(self, "estimating", None)
        if isinstance(text, str) and dialog is not None and shiboken6.isValid(dialog) and dialog.pages:
            dialog.pages.show_preview(text)

    def autosave_script(self, tab: EditorTab, exported: Path) -> None:
        """Write '<name>.es' beside a template export: the script with the viewport camera and the seed."""
        target = autosave_path(exported)
        if target.exists() and not self._overwrite(target):
            return
        text = script_with_settings(tab.text(), self.w.viewport.camera(), tab.seed, exported, tab.dialect == 2,
                                    datetime.now())  # fmt: skip

        def run(ctx: JobContext) -> Path:
            target.write_text(text, encoding="utf-8")
            return target

        self.w.runner.submit(FunctionJob(f"save {target.name}", Lane.IO, run)).finished.connect(self._script_saved)

    @Slot(object)
    def _script_saved(self, path: object) -> None:
        self.w.console.info(f"Script saved with seed and camera: {path}")

    def _overwrite(self, target: Path) -> bool:
        buttons = QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        question = tr("Overwrite {path}?").format(path=target)
        answer = QMessageBox.warning(self.w, tr("File Exists"), question, buttons, QMessageBox.StandardButton.Cancel)
        return bool(answer == QMessageBox.StandardButton.Ok)

    def _change_path(self, exporter: Exporter, path: Path) -> Path | None:
        answer = self.ask_path(exporter, path, every_format=False)
        return answer[1] if answer else None

    def start(self, name: str | None = None) -> None:
        """Export ▸ <format>… (``name``) or File ▸ Export As… (None: the format is chosen in the dialog)."""
        tab = self.w.tabs.current()
        if tab is None or tab.outcome is None:
            self.w.show_message("Build the script first (F5), then export.")
            return
        exporter = EXPORTERS[name or self.last_format]
        suggestion = self.paths.suggest(KIND, stem_for(tab.path) + exporter.extensions[0], tab.path)
        answer = self.ask_path(exporter, suggestion, every_format=name is None)
        if answer is None:
            return
        exporter, path = answer
        values = self._last.get(exporter.name, {})
        scene = tab.outcome.scene
        dialog = ExportDialog(exporter, path, scene, values, self._change_path, self.w, self.w.themes.theme)
        self.estimating = dialog
        dialog.estimate_wanted.connect(lambda options: self._estimate(scene, dialog, options))
        dialog.preview_wanted.connect(lambda options: self._preview(scene, options))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if dialog.autosave():
            self.autosave_script(tab, dialog.path)
        options = dialog.form.values()
        self._last[exporter.name], self.last_format = options, exporter.name
        scene, camera = tab.outcome.scene, self.w.viewport.camera()
        request = ExportRequest(scene, dialog.path, exporter.name, options, camera)
        self.requests[dialog.path] = request
        self.commands[dialog.path] = dialog.run_after.text().strip()
        self.service.request(request)
        self.w.render_queue.track_export(f"{exporter.title} · {len(scene):,} objects", dialog.path)
        self.w.show_message(f"Exporting {dialog.path.name}…")

    def check_mesh(self) -> None:
        """Export ▸ Check Mesh: MeshLab's measures of the structure as a mesh would be exported (io lane)."""
        tab = self.w.tabs.current()
        if tab is None or tab.outcome is None:
            self.w.show_message(tr("Build the script first (F5), then check the mesh."))
            return
        scene = tab.outcome.scene

        def run(ctx: JobContext) -> MeshCheck:
            ctx.progress(0.0, "tessellating")
            return check_mesh(tessellate(scene))

        handle = self.w.runner.submit(FunctionJob("check mesh", Lane.IO, run, key="check-mesh"))
        handle.finished.connect(self._checked)
        handle.failed.connect(self._failed_check)
        self.w.show_message(tr("Checking the mesh with MeshLab…"))

    @Slot(object)
    def _checked(self, check: object) -> None:
        if isinstance(check, MeshCheck):
            verdict = tr("watertight: ready to print") if check.watertight else tr("not watertight (see below)")
            box = QMessageBox(QMessageBox.Icon.Information, tr("Check Mesh"), tr("The mesh is {verdict}.").format(
                verdict=verdict), parent=self.w)  # fmt: skip
            box.setDetailedText("\n".join(f"{label}: {value}" for label, value in check.rows()))
            box.setInformativeText(tr("An STL export with the 'print-ready' clean-up, or 'Watertight union', repairs "
                                      "most problems."))  # fmt: skip
            box.open()

    @Slot(object)
    def _failed_check(self, info: object) -> None:
        message = info.message if isinstance(info, ErrorInfo) else str(info)
        self.w.show_message(tr("Check Mesh failed: {error}").format(error=message))

    @Slot(str, float, str)
    def _progress(self, path: str, fraction: float, text: str) -> None:
        self.w.status.showMessage(f"Exporting {Path(path).name}: {text}")
        self.w.render_queue.export_progress(Path(path), fraction)

    @Slot(str)
    def _cancelled(self, path: str) -> None:
        self.w.render_queue.export_ended(Path(path), "cancelled")

    @Slot(object)
    def _finished(self, report: object) -> None:
        if isinstance(report, ExportReport):
            self.w.render_queue.export_ended(report.path, "done")
            counts = ", ".join(f"{k} {v:,}" for k, v in report.counts.items())
            self.w.notify_file(f"Exported {report.path.name}" + (f" ({counts})" if counts else ""), report.path)
            for warning in report.warnings:
                self.w.toasts.show(warning)
            request = self.requests.pop(report.path, None)
            command = self.commands.pop(report.path, "")
            if command:
                self.run_command(tr("this export"), command, report.path)
            if request is not None and request.exporter == "template":
                self.run_after(str(request.options.get("template", "")), report.path)
            if request is not None and request.exporter == "blender":
                self._offer_blender(report.path)
            elif report.path.suffix.lower() in MESHLAB.opens:
                self._offer(MESHLAB, report.path)

    def _offer_blender(self, script: Path) -> None:
        self._offer(BLENDER, script)

    def _offer(self, app: ExternalApp, path: Path) -> None:
        """A toast with "Open in <app>" when the app is installed."""
        if self._find(app) is not None:
            title = tr("Open in {app}").format(app=app.name)
            self.w.toasts.show(tr("{name} is ready").format(name=path.name), (title, lambda: self.open_in(app, path)))

    def _find(self, app: ExternalApp) -> str | None:
        configured = str(self.w.settings.value(app.key, ""))
        return find_blender(configured) if app is BLENDER else find_app(app, configured)

    def open_in(self, app: ExternalApp, path: Path) -> None:
        """Open ``path`` in ``app`` (a non-blocking process; its output goes to the Console)."""
        program = self._find(app)
        if program is None:
            self.w.show_message(tr("{app} was not found: set its path in Preferences ▸ Paths.").format(app=app.name))
            return
        self.w.processes.start_program(program, app.arguments(path), path.parent)

    def open_in_blender(self, script: Path) -> None:
        """Run the exported script in Blender."""
        self.open_in(BLENDER, script)

    def run_after(self, template: str, file: Path) -> None:
        """Run the template's 'runAfter' program on the exported file (after asking, once per command)."""
        path = all_templates().get(template)
        command = load_template(path).run_after if path is not None else ""
        if command:
            self.run_command(tr("The template '{name}'").format(name=template), command, file)

    def run_command(self, source: str, command: str, file: Path) -> None:
        """Run a 'run after' command on the exported file: a template's or the export sheet's (e.g. a PyMeshLab
        script); asked once per command and session, because it can run any program."""
        expanded = expand_command(command, file)
        if command not in self.allowed and not self._confirm(source, command, expanded):
            return
        self.allowed.add(command)
        self.w.processes.start(expanded, file.parent)

    def _confirm(self, source: str, command: str, expanded: str) -> bool:
        """Commands can run any program: the user sees the command (and unset variables) before it runs."""
        missing = missing_variables(command)
        note = tr("Not set: {names}").format(names=", ".join(missing)) + "\n\n" if missing else ""
        question = tr("{source} runs a program on the exported file:").format(source=source)
        question += f"\n\n{expanded}\n\n{note}" + tr("It can run any program. Run it?")
        buttons = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        answer = QMessageBox.question(self.w, tr("Run After Export"), question, buttons)
        return bool(answer == QMessageBox.StandardButton.Yes)

    @Slot(str, object)
    def _failed(self, path: str, info: object) -> None:
        message = info.message if isinstance(info, ErrorInfo) else str(info)
        self.w.render_queue.export_ended(Path(path), "failed", message)
        self.w.show_message(f"Export of {Path(path).name} failed: {message}")
