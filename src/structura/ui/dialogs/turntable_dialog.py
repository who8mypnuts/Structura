"""Render ▸ Turntable… (PLAN F2): a looping orbit of the current view, written as timeline keys."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QWidget,
)

from ...core.animation.paths import Turntable
from ..i18n import tr

DIRECTIONS = ("counter-clockwise", "clockwise")


class TurntableDialog(QDialog):
    def __init__(self, fps: float, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Turntable"))
        self.seconds, self.fps, self.turns = QDoubleSpinBox(), QDoubleSpinBox(), QDoubleSpinBox()
        self.seconds.setRange(0.5, 600.0)
        self.seconds.setValue(5.0)
        self.seconds.setSuffix(" s")
        self.fps.setRange(1.0, 240.0)
        self.fps.setValue(fps)
        self.turns.setRange(0.05, 100.0)
        self.turns.setValue(1.0)
        self.turns.setSingleStep(0.25)
        self.direction = QComboBox()
        self.direction.addItems([tr(d) for d in DIRECTIONS])
        self.tilt, self.elevation = QCheckBox(tr("Set the height")), QSpinBox()
        self.elevation.setRange(-89, 89)
        self.elevation.setValue(20)
        self.elevation.setSuffix(" °")
        self.elevation.setEnabled(False)
        self.tilt.toggled.connect(self.elevation.setEnabled)
        self.ease = QCheckBox(tr("Ease in and out (stops at the end instead of looping)"))
        self.zoom = QSpinBox()
        self.zoom.setRange(20, 300)
        self.zoom.setValue(100)
        self.zoom.setSuffix(" %")
        self.zoom.setToolTip(tr("The camera's distance at the end, as a share of the start (focus on the target "
                                "follows it)"))  # fmt: skip
        self.render_now = QCheckBox(tr("Render the animation now"))
        self.render_now.setChecked(True)
        note = QLabel(tr("The camera orbits the current view's target. The timeline's camera path is replaced; "
                         "its range becomes one seamless loop."))  # fmt: skip
        note.setObjectName("Muted")
        note.setWordWrap(True)
        form = QFormLayout(self)
        form.addRow(note)
        form.addRow(tr("Duration"), self.seconds)
        form.addRow(tr("Frames per second"), self.fps)
        form.addRow(tr("Turns"), self.turns)
        form.addRow(tr("Direction"), self.direction)
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
        frames = max(2, round(self.seconds.value() * self.fps.value()))
        elevation = float(self.elevation.value()) if self.tilt.isChecked() else None
        clockwise = self.direction.currentIndex() == 1
        return Turntable(frames, self.turns.value(), clockwise, elevation, start, self.ease.isChecked(),
                         self.zoom.value() / 100.0)  # fmt: skip
