"""Export menu actions: file dialog → options form (from the exporter's ParamSpecs) → ExportService job."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QVBoxLayout

from ..export.api import EXPORTERS
from ..export.base import Exporter, ExportReport
from ..services.export import ExportRequest, ExportService
from ..services.jobs import ErrorInfo
from .widgets.param_form import ParamForm

if TYPE_CHECKING:
    from .app_window import MainWindow

MENU_ORDER = ("obj", "ply", "stl", "3mf", "gltf", "usd", "x3d", "vrml", "blender", "template", "obj-legacy")


class OptionsDialog(QDialog):
    def __init__(self, exporter: Exporter, parent: MainWindow, values: dict[str, object]) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Export — {exporter.title}")
        self.form = ParamForm(exporter.params, values)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self.form)
        layout.addWidget(buttons)


class ExportActions(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        self.service = ExportService(window.runner)
        self.service.finished.connect(self._finished)
        self.service.failed.connect(self._failed)
        self.service.progress.connect(self._progress)
        self._last: dict[str, dict[str, object]] = {}

    def exporters(self) -> list[Exporter]:
        """The registered exporters: the curated order first, then any others (plugins) by name."""
        rest = sorted(set(EXPORTERS) - set(MENU_ORDER))
        return [EXPORTERS[name] for name in (*MENU_ORDER, *rest) if name in EXPORTERS]

    def start(self, name: str) -> None:
        tab = self.w.tabs.current()
        if tab is None or tab.outcome is None:
            self.w.show_message("Build the script first (F5), then export.")
            return
        exporter = EXPORTERS[name]
        patterns = " ".join(f"*{e}" for e in exporter.extensions)
        suggested = (tab.path.stem if tab.path else "structure") + exporter.extensions[0]
        target, _ = QFileDialog.getSaveFileName(self.w, exporter.title, suggested, f"{exporter.title} ({patterns})")
        if not target:
            return
        dialog = OptionsDialog(exporter, self.w, self._last.get(name, {}))
        if exporter.params and dialog.exec() != QDialog.DialogCode.Accepted:
            return
        options = dialog.form.values()
        self._last[name] = options
        scene, camera = tab.outcome.scene, self.w.viewport.camera()
        self.service.request(ExportRequest(scene, Path(target), name, options, camera))
        self.w.show_message(f"Exporting {Path(target).name}…")

    @Slot(str, float, str)
    def _progress(self, path: str, fraction: float, text: str) -> None:
        self.w.status.showMessage(f"Exporting {Path(path).name}: {text}")

    @Slot(object)
    def _finished(self, report: object) -> None:
        if isinstance(report, ExportReport):
            counts = ", ".join(f"{k} {v:,}" for k, v in report.counts.items())
            self.w.show_message(f"Exported {report.path.name}" + (f" ({counts})" if counts else ""))

    @Slot(str, object)
    def _failed(self, path: str, info: object) -> None:
        message = info.message if isinstance(info, ErrorInfo) else str(info)
        self.w.show_message(f"Export of {Path(path).name} failed: {message}")
