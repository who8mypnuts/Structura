"""Render ▸ Turntable… (PLAN F2): a looping orbit of the current view, written as timeline keys."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QWidget,
)

from ...core.animation.paths import Turntable
from ..i18n import tr
from ..widgets.fields import combo_box, spin_box

DIRECTIONS = ("counter-clockwise", "clockwise")


class TurntableDialog(QDialog):
    """Render ▸ Turntable…: duration, frame rate, turns, direction, height, distance and easing."""

    def __init__(self, fps: float, parent: QWidget | None = None) -> None:
        """Builds the dialog.

        Args:
            fps: The timeline's frame rate (the default).
            parent: The parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle(tr("Turntable"))
        self.seconds = spin_box(0.5, 600.0, 1, tr("Duration"), " s", value=5.0)
        self.fps = spin_box(1.0, 240.0, 2, tr("Frames per second"), value=fps)
        self.turns = spin_box(0.05, 100.0, 2, tr("Turns"), value=1.0)
        self.turns.setSingleStep(0.25)
        self.direction = combo_box([tr(d) for d in DIRECTIONS], tr("Direction"))
        self.tilt = QCheckBox(tr("Set the height"))
        self.elevation = spin_box(-89.0, 89.0, 0, tr("Height"), " °", value=20.0)
        self.elevation.setEnabled(False)
        self.tilt.toggled.connect(self.elevation.setEnabled)
        self.zoom = spin_box(20.0, 300.0, 0, tr("Distance at the end"), " %", value=100.0)
        self.zoom.setToolTip(tr("The camera's distance at the end, as a share of the start (focus on the target "
                                "follows it)"))  # fmt: skip
        self.ease = QCheckBox(tr("Ease in and out (stops at the end instead of looping)"))
        self.render_now = QCheckBox(tr("Render the animation now"))
        self.render_now.setChecked(True)
        self._layout()

    def _layout(self) -> None:
        """The note, the fields in a form, and Create / Cancel."""
        note = QLabel(tr("The camera orbits the current view's target. The timeline's camera path is replaced; "
                         "its range becomes one seamless loop."))  # fmt: skip
        note.setObjectName("Muted")
        note.setWordWrap(True)
        form = QFormLayout(self)
        form.addRow(note)
        for label, widget in ((tr("Duration"), self.seconds), (tr("Frames per second"), self.fps),
                              (tr("Turns"), self.turns), (tr("Direction"), self.direction)):  # fmt: skip
            form.addRow(label, widget)
        form.addRow(self.tilt, self.elevation)
        form.addRow(tr("Distance at the end"), self.zoom)
        form.addRow(self.ease)
        form.addRow(self.render_now)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("Create"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def choice(self, start: int = 0) -> Turntable:
        """Returns the turntable the dialog describes.

        Args:
            start: The first frame (the timeline's start).
        """
        frames = max(2, round(self.seconds.value() * self.fps.value()))
        elevation = float(self.elevation.value()) if self.tilt.isChecked() else None
        clockwise = self.direction.currentIndex() == 1
        return Turntable(frames, self.turns.value(), clockwise, elevation, start, self.ease.isChecked(),
                         self.zoom.value() / 100.0)  # fmt: skip
