"""The window's side of a running '#javascript' script (docs/16 §3): Debug.Info / Message / progress, scenes
from Builder.build and World, Debug.waitForMouseButton (a click in the viewport answers) and the one-time
confirmation of Builder.execute. The script process waits for answers; the GUI thread never does."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QObject, Qt, Slot
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QMessageBox

from ..services.script_process import ScriptProcess
from .i18n import tr

if TYPE_CHECKING:
    from .app_window import MainWindow


class ScriptUi(QObject):
    def __init__(self, window: MainWindow, requests: ScriptProcess) -> None:
        super().__init__(window)
        self.w, self.requests = window, requests
        self.caption = ""
        self.waiting = False
        requests.info.connect(self._info)
        requests.message.connect(self._message)
        requests.progress.connect(self._progress)
        requests.scene.connect(self._scene)
        requests.click.connect(self._wait_for_click)
        requests.confirm.connect(self._confirm)

    @Slot(str)
    def _info(self, text: str) -> None:
        self.w.console.info(text)

    @Slot(str)
    def _message(self, text: str) -> None:
        self.w.console.info(text)
        self.w.toasts.show(text)

    @Slot(object, object)
    def _progress(self, caption: object, fraction: object) -> None:
        if caption is None and fraction is None:
            self.w.status.clearMessage()
            return
        self.caption = str(caption) if caption is not None else self.caption
        done = f" {float(fraction):.0%}" if isinstance(fraction, float) else ""
        self.w.status.showMessage(self.caption + done)

    @Slot(object, object)
    def _scene(self, scene: object, preview: object) -> None:
        first = self.w.viewport.scene is None
        self.w.viewport.set_scene(scene, preview, None)  # type: ignore[arg-type]
        if first:
            self.w.viewport.frame_all()

    @Slot()
    def _wait_for_click(self) -> None:
        self.waiting = True
        self.w.status.showMessage(tr("Left click in the viewport to continue, right click to stop."))
        self.w.viewport.installEventFilter(self)
        for child in self.w.viewport.findChildren(QObject):
            child.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if self.waiting and isinstance(event, QMouseEvent) and event.type() == QEvent.Type.MouseButtonPress:
            self.click(event.button() == Qt.MouseButton.LeftButton)
            return True
        return False

    def click(self, left: bool) -> None:
        """A click answered Debug.waitForMouseButton (left: continue)."""
        self.waiting = False
        self.w.status.clearMessage()
        self.requests.answer(left)

    @Slot(str)
    def _confirm(self, command: str) -> None:
        question = tr("The script wants to run:") + f"\n\n{command}\n\n" + tr("Scripts can run any program. Run it?")
        buttons = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        answer = QMessageBox.question(self.w, tr("Run a Program"), question, buttons)
        self.requests.answer(answer == QMessageBox.StandardButton.Yes)
