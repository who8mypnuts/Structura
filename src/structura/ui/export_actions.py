"""Export menu actions: Save As dialog → export sheet (destination, contents, options) → ExportService job."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QDialog, QMessageBox

from ..export.api import EXPORTERS
from ..export.base import Exporter, ExportReport, exporter_for
from ..export.templates.run_after import expand_command, missing_variables
from ..export.templates.template_file import bundled_templates, load_template
from ..services.export import ExportRequest, ExportService
from ..services.jobs import ErrorInfo
from .dialogs.export_dialog import ExportDialog
from .i18n import tr
from .save_paths import SavePaths, stem_for, with_extension

if TYPE_CHECKING:
    from .app_window import MainWindow

MENU_ORDER = ("obj", "ply", "stl", "3mf", "gltf", "usd", "x3d", "vrml", "blender", "template", "obj-legacy")
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
        self._last: dict[str, dict[str, object]] = {}
        self.last_format = "obj"
        self.requests: dict[Path, ExportRequest] = {}  # by target path, for 'run after' commands
        self.allowed: set[str] = set()  # 'run after' commands the user allowed this session

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
        dialog = ExportDialog(exporter, path, tab.outcome.scene, values, self._change_path, self.w)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        options = dialog.form.values()
        self._last[exporter.name], self.last_format = options, exporter.name
        scene, camera = tab.outcome.scene, self.w.viewport.camera()
        request = ExportRequest(scene, dialog.path, exporter.name, options, camera)
        self.requests[dialog.path] = request
        self.service.request(request)
        self.w.show_message(f"Exporting {dialog.path.name}…")

    @Slot(str, float, str)
    def _progress(self, path: str, fraction: float, text: str) -> None:
        self.w.status.showMessage(f"Exporting {Path(path).name}: {text}")

    @Slot(object)
    def _finished(self, report: object) -> None:
        if isinstance(report, ExportReport):
            counts = ", ".join(f"{k} {v:,}" for k, v in report.counts.items())
            self.w.notify_file(f"Exported {report.path.name}" + (f" ({counts})" if counts else ""), report.path)
            for warning in report.warnings:
                self.w.toasts.show(warning)
            request = self.requests.pop(report.path, None)
            if request is not None and request.exporter == "template":
                self.run_after(str(request.options.get("template", "")), report.path)

    def run_after(self, template: str, file: Path) -> None:
        """Run the template's 'runAfter' program on the exported file (after asking, once per command)."""
        path = bundled_templates().get(template)
        command = load_template(path).run_after if path is not None else ""
        if not command:
            return
        expanded = expand_command(command, file)
        if command not in self.allowed and not self._confirm(template, command, expanded):
            return
        self.allowed.add(command)
        self.w.processes.start(expanded, file.parent)

    def _confirm(self, template: str, command: str, expanded: str) -> bool:
        """Templates can run any program: the user sees the command (and unset variables) before it runs."""
        missing = missing_variables(command)
        note = tr("Not set: {names}").format(names=", ".join(missing)) + "\n\n" if missing else ""
        question = tr("The template '{name}' runs a program on the exported file:").format(name=template)
        question += f"\n\n{expanded}\n\n{note}" + tr("Templates can run any program. Run it?")
        buttons = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        answer = QMessageBox.question(self.w, tr("Run After Export"), question, buttons)
        return bool(answer == QMessageBox.StandardButton.Yes)

    @Slot(str, object)
    def _failed(self, path: str, info: object) -> None:
        message = info.message if isinstance(info, ErrorInfo) else str(info)
        self.w.show_message(f"Export of {Path(path).name} failed: {message}")
