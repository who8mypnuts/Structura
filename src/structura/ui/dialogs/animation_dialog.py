"""Render Animation dialog (docs/16 §2.3): where the frames go, which frames, quality, and an optional video."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)

from ...core.animation.timeline import Timeline
from ...render.video import VIDEO_FORMATS
from ..i18n import tr

NO_VIDEO = "no video"


@dataclass(frozen=True)
class AnimationChoice:
    pattern: Path
    frames: range
    samples: int
    video: Path | None


class AnimationDialog(QDialog):
    def __init__(self, timeline: Timeline, folder: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Render Animation"))
        self.pattern = QLineEdit(str(folder / "frames" / "frame.png"))
        self.pattern.setAccessibleName(tr("Frame files"))
        browse = QPushButton(tr("Browse…"))
        browse.clicked.connect(self._browse)
        path_row = QHBoxLayout()
        path_row.addWidget(self.pattern, 1)
        path_row.addWidget(browse)
        self.first, self.last, self.samples = QSpinBox(), QSpinBox(), QSpinBox()
        for spin in (self.first, self.last):
            spin.setRange(-100_000, 100_000)
        self.first.setValue(timeline.start)
        self.last.setValue(timeline.end)
        self.samples.setRange(1, 65536)
        self.samples.setValue(32)
        self.video = QComboBox()
        self.video.addItems([NO_VIDEO, *(s.lstrip(".") for s in VIDEO_FORMATS)])
        form = QFormLayout(self)
        form.addRow(tr("Frames"), path_row)
        form.addRow(tr("First frame"), self.first)
        form.addRow(tr("Last frame"), self.last)
        form.addRow(tr("Samples per pixel"), self.samples)
        form.addRow(tr("Video"), self.video)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Render")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _browse(self) -> None:
        name, _ = QFileDialog.getSaveFileName(self, "Frame files", self.pattern.text(), "Images (*.png *.jpg *.exr)")
        if name:
            self.pattern.setText(name)

    def choice(self) -> AnimationChoice:
        pattern = Path(self.pattern.text())
        kind = self.video.currentText()
        video = None if kind == NO_VIDEO else pattern.with_name(f"{pattern.stem}.{kind}")
        first, last = self.first.value(), max(self.first.value(), self.last.value())
        return AnimationChoice(pattern, range(first, last + 1), self.samples.value(), video)
