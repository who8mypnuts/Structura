"""Render Report action (docs/09 §11): a save dialog, then every statistic of the view's last finished
render — scene, camera, render settings and performance — in the chosen format.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QFileDialog

from ..render.report import ReportContext, build_report, write_report
from ..services.render import RenderUpdate
from .documents import EditorTab
from .reporting import write_pdf
from .save_paths import suggested_path

if TYPE_CHECKING:
    from .app_window import MainWindow

FILTERS = "HTML (*.html);;Markdown (*.md);;Plain text (*.txt);;PDF (*.pdf);;JSON (*.json)"


def _context(tab: EditorTab, update: RenderUpdate) -> ReportContext:
    assert tab.outcome is not None and update.settings is not None
    script = tab.text()
    return ReportContext(
        scene=tab.outcome.scene,
        stats=tab.outcome.stats,
        settings=update.settings,
        build_seed=tab.outcome.seed,
        camera=update.camera,
        scene_stats=update.scene_stats,
        device=update.device,
        achieved_samples=update.progress.samples,
        seconds=update.progress.seconds,
        active=update.progress.active,
        denoiser=update.denoiser,
        script_name=tab.display_name,
        script_sha256=hashlib.sha256(script.encode("utf-8")).hexdigest(),
    )


class ReportActions(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window

    def save_dialog(self) -> None:
        tab, update = self.w.tabs.current(), self.w.render_view.last
        if tab is None or tab.outcome is None or update is None or update.settings is None:
            self.w.show_message("Render the view first (F9), then create a report.")
            return
        suggested = suggested_path(tab.path, "render-report.html")
        name, _ = QFileDialog.getSaveFileName(self.w, "Render report", suggested, FILTERS)
        if not name:
            return
        path, data = Path(name), build_report(_context(tab, update))
        if path.suffix.lower() == ".pdf":
            write_pdf(data, path)
        else:
            write_report(data, path)
        self.w.show_message(f"Wrote {path.name}")
