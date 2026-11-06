"""Timeline panel: transport, frame range, fps, key buttons and the keyframe strip (docs/16 §2).

The panel emits intents only; TimelineActions owns the timeline and applies them to the current tab.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Signal, Slot
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QMenu,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ....core.animation.timeline import Interp, Timeline
from ...i18n import tr
from .strip import TimelineStrip

MAX_FRAME = 100_000


def _spin(prefix: str, low: int = -MAX_FRAME, high: int = MAX_FRAME) -> QSpinBox:
    spin = QSpinBox()
    spin.setRange(low, high)
    spin.setPrefix(prefix)
    spin.setKeyboardTracking(False)
    return spin


def _button(text: str, tip: str) -> QToolButton:
    button = QToolButton()
    button.setText(text)
    button.setToolTip(tip)
    button.setAutoRaise(True)
    return button


class TimelinePanel(QWidget):
    frame_requested = Signal(int)
    play_toggled = Signal(bool)
    range_edited = Signal(int, int, float)  # start, end, fps
    key_camera = Signal()
    key_params = Signal()
    render_animation = Signal()
    key_action = Signal(str, int, str)  # target, frame, 'constant' | 'linear' | 'smooth' | 'delete'

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.strip = TimelineStrip()
        self.play = _button("▶", "Play / pause (Space in the timeline)")
        self.play.setCheckable(True)
        self.first, self.last = _button("⏮", "First frame"), _button("⏭", "Last frame")
        self.frame, self.start, self.end = _spin("frame "), _spin("start "), _spin("end ")
        self.fps = QDoubleSpinBox()
        self.fps.setRange(1.0, 240.0)
        self.fps.setSuffix(" fps")
        self.fps.setKeyboardTracking(False)
        self.fps.setAccessibleName(tr("Frames per second"))
        self.frame.setAccessibleName(tr("Current frame"))
        self.start.setAccessibleName(tr("First frame"))
        self.end.setAccessibleName(tr("Last frame"))
        self.strip.setAccessibleName(tr("Keyframes"))
        self.key_cam = QPushButton(tr("◆ Camera"))
        self.key_cam.setToolTip(tr("Key the viewport camera at this frame"))
        self.key_all = QPushButton(tr("◆ Parameters"))
        self.key_all.setToolTip(tr("Key every parameter at this frame"))
        self.render_button = QPushButton(tr("Render Animation…"))
        self._layout()
        self._connect()
        self.timeline = Timeline()

    def _layout(self) -> None:
        bar = QHBoxLayout()
        bar.setContentsMargins(4, 2, 4, 2)
        transport: tuple[QWidget, ...] = (self.first, self.play, self.last, self.frame, self.start, self.end, self.fps)
        for widget in transport:
            bar.addWidget(widget)
        bar.addStretch(1)
        for button in (self.key_cam, self.key_all, self.render_button):
            bar.addWidget(button)
        scroll = QScrollArea()
        scroll.setAccessibleName(tr("Keyframes"))
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.strip)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(bar)
        layout.addWidget(scroll, 1)

    def _connect(self) -> None:
        self.strip.scrubbed.connect(self.frame_requested)
        self.strip.key_menu.connect(self._key_menu)
        self.frame.valueChanged.connect(self.frame_requested)
        self.first.clicked.connect(lambda: self.frame_requested.emit(self.timeline.start))
        self.last.clicked.connect(lambda: self.frame_requested.emit(self.timeline.end))
        self.play.toggled.connect(self.play_toggled)
        for spin in (self.start, self.end, self.fps):
            spin.valueChanged.connect(self._range_edited)
        self.key_cam.clicked.connect(self.key_camera)
        self.key_all.clicked.connect(self.key_params)
        self.render_button.clicked.connect(self.render_animation)

    def show_state(self, timeline: Timeline, frame: int, playing: bool) -> None:
        """Reflect the model without emitting."""
        self.timeline = timeline
        widgets = (self.frame, self.start, self.end, self.fps, self.play)
        for w in widgets:
            w.blockSignals(True)
        self.start.setValue(timeline.start)
        self.end.setValue(timeline.end)
        self.frame.setRange(timeline.start, timeline.end)
        self.frame.setValue(frame)
        self.fps.setValue(timeline.fps)
        self.play.setChecked(playing)
        self.play.setText("⏸" if playing else "▶")
        for w in widgets:
            w.blockSignals(False)
        self.strip.show_timeline(timeline, frame)

    @Slot()
    def _range_edited(self) -> None:
        self.range_edited.emit(self.start.value(), max(self.end.value(), self.start.value()), self.fps.value())

    @Slot(list, int, QPoint)
    def _key_menu(self, targets: list[str], frame: int, at: QPoint) -> None:
        menu = QMenu(self)
        for interp in Interp:
            action = menu.addAction(f"Interpolation: {interp.value}")
            action.triggered.connect(lambda _=False, i=interp.value: self._emit(targets, frame, i))
        menu.addSeparator()
        menu.addAction("Delete Key").triggered.connect(lambda: self._emit(targets, frame, "delete"))
        menu.popup(at)

    def _emit(self, targets: list[str], frame: int, action: str) -> None:
        for target in targets:
            self.key_action.emit(target, frame, action)
