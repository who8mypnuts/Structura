"""Render Animation (docs/16 §2.3): the dialog, the device-lane job, and its progress in the Render view."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QDialog

from ..render.animation import Animation
from ..render.settings import AUTO_PASSES
from ..services.animation import AnimationProgress, AnimationRequest, AnimationService
from ..services.jobs import ErrorInfo
from .dialogs.animation_dialog import AnimationDialog

if TYPE_CHECKING:
    from .app_window import MainWindow


class AnimationActions(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        self.service = AnimationService(window.runner, window.renders.backends)
        self.service.progress.connect(self._on_progress)
        self.service.finished.connect(self._on_finished)
        self.service.failed.connect(self._on_failed)

    def animation(self, samples: int) -> Animation | None:
        """The current tab as an Animation: its timeline, seed, parameters, the viewport camera, and the
        Render view's size and integrator with the Render Settings overrides."""
        tab, source = self.w.tabs.current(), self.w.render_source()
        if tab is None or source is None:
            return None
        _, camera, settings, text = source
        overrides = {**tab.render_overrides, "width": settings.width, "height": settings.height,
                     "integrator": settings.integrator, "samples": samples,
                     "samples_per_pass": AUTO_PASSES}  # fmt: skip
        folder = tab.path.parent if tab.path else None
        return Animation(text, tab.timeline, tab.seed, dict(tab.params), folder, camera, overrides)

    @Slot()
    def render(self) -> None:
        tab = self.w.tabs.current()
        if tab is None or tab.outcome is None:
            self.w.show_message("Build the script first (F5), then render its animation.")
            return
        folder = tab.path.parent if tab.path else Path.home()
        dialog = AnimationDialog(tab.timeline, folder, self.w)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        choice = dialog.choice()
        anim = self.animation(choice.samples)
        if anim is None:
            return
        device = self.w.render_view.device.currentText()
        self.service.request(AnimationRequest(anim, choice.frames, choice.pattern, choice.video, device))
        self.w.views.setCurrentWidget(self.w.render_view)
        self.w.show_message(f"Rendering {len(choice.frames)} frames to {choice.pattern.parent}")

    def cancel(self) -> None:
        self.service.cancel_all()

    @Slot(object)
    def _on_progress(self, progress: object) -> None:
        if isinstance(progress, AnimationProgress):
            text = f"animation frame {progress.frame} ({progress.done}/{progress.total}) → {progress.path.name}"
            self.w.render_view.show_image(progress.image, text)

    @Slot(object)
    def _on_finished(self, paths: object) -> None:
        count = len(paths) if isinstance(paths, list) else 0
        self.w.show_message(f"Animation finished: {count} files written")

    @Slot(object)
    def _on_failed(self, info: object) -> None:
        if isinstance(info, ErrorInfo):
            self.w.show_message(f"Animation failed: {info.message}")
