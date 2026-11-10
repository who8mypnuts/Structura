"""Render Animation (docs/16 §2.3): the dialog, the device-lane job, and its progress in the Render view; and
the camera paths that make an animation in one step (PLAN F2): a turntable, or a path through saved views."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QDialog, QInputDialog

from ..core.animation.paths import path_through, turntable
from ..render.animation import Animation
from ..render.settings import AUTO_PASSES
from ..services.animation import AnimationProgress, AnimationRequest, AnimationService
from ..services.jobs import ErrorInfo
from .dialogs.animation_dialog import AnimationDialog
from .dialogs.turntable_dialog import TurntableDialog
from .i18n import tr

if TYPE_CHECKING:
    from .app_window import MainWindow


class AnimationActions(QObject):
    """Render Animation, turntables and camera paths: the dialogs, the animation job and its progress."""

    def __init__(self, window: MainWindow) -> None:
        """Creates the animation service and shows its progress in the Render view.

        Args:
            window: The main window.
        """
        super().__init__(window)
        self.w = window
        self.service = AnimationService(window.runner, window.renders.backends)
        self.service.progress.connect(self._on_progress)
        self.service.finished.connect(self._on_finished)
        self.service.failed.connect(self._on_failed)

    def animation(self, samples: int) -> Animation | None:
        """Returns the current tab as an Animation, or None without a tab or a built scene.

        The animation has the tab's timeline, seed and parameters, the viewport camera, and the Render view's size,
        integrator, exposure, view transform and look, with the Render Settings overrides.

        Args:
            samples: Samples per pixel of every frame.
        """
        tab, source = self.w.tabs.current(), self.w.render_actions.render_source()
        if tab is None or source is None:
            return None
        _, camera, settings, text = source
        shown = self.w.render_view.display(settings)  # frames look like the Render view: exposure, view, look
        overrides = {**tab.render_overrides, "width": settings.width, "height": settings.height,
                     "integrator": settings.integrator, "samples": samples, "samples_per_pass": AUTO_PASSES,
                     "exposure": shown.exposure, "view": shown.view, "post": shown.post}  # fmt: skip
        folder = tab.path.parent if tab.path else None
        return Animation(text, tab.timeline, tab.seed, dict(tab.params), folder, camera, overrides)

    @Slot()
    def render(self) -> None:
        """Asks for the frames and the output (the Animation dialog), then renders the animation of the built script."""
        tab = self.w.built_tab(tr("render its animation"))
        if tab is None:
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

    @Slot()
    def turntable(self) -> None:
        """Render ▸ Turntable…: key an orbit of the viewport camera, then (by default) render it."""
        tab = self.w.built_tab(tr("make a turntable"))
        if tab is None:
            return
        dialog = TurntableDialog(tab.timeline.fps, self.w)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        spec = dialog.choice(tab.timeline.start)
        timeline = replace(tab.timeline, fps=dialog.fps.value())
        tab.timeline = turntable(timeline, self.w.viewport.camera(), spec)
        self.w.timeline.refresh()
        self.w.show_message(tr("Turntable keyed: {frames} frames").format(frames=spec.frames))
        if dialog.render_now.isChecked():
            self.render()

    @Slot()
    def camera_path(self) -> None:
        """Render ▸ Camera Path from Saved Views…: a smooth path through the Camera panel's saved views."""
        tab = self.w.tabs.current()
        if tab is None:
            return
        views = list(tab.bookmarks.values())
        if len(views) < 2:
            self.w.show_message(tr("Save two views or more in the Camera panel first."))
            return
        frames, ok = QInputDialog.getInt(self.w, tr("Camera Path"), tr("Frames from one saved view to the next:"),
                                         48, 1, 100_000)  # fmt: skip
        if ok:
            tab.timeline = path_through(tab.timeline, views, frames, tab.timeline.start)
            self.w.timeline.refresh()
            self.w.show_message(tr("Camera path keyed through {count} saved views").format(count=len(views)))

    def cancel(self) -> None:
        self.service.cancel_all()

    @Slot(object)
    def _on_progress(self, progress: object) -> None:
        if isinstance(progress, AnimationProgress):
            text = f"animation frame {progress.frame} ({progress.done}/{progress.total}) → {progress.path.name}"
            self.w.render_view.show_image(progress.image, text, progress.done / max(1, progress.total))

    @Slot(object)
    def _on_finished(self, paths: object) -> None:
        count = len(paths) if isinstance(paths, list) else 0
        self.w.render_view.activity.emit("")
        self.w.show_message(f"Animation finished: {count} files written")

    @Slot(object)
    def _on_failed(self, info: object) -> None:
        if isinstance(info, ErrorInfo):
            self.w.render_view.activity.emit("")
            self.w.show_message(f"Animation failed: {info.message}")
