"""The keyframe strip: a frame ruler, one row of ◆ keys per track, and the playhead.

Click or drag to scrub; right-click a key for its interpolation or to delete it. Colours come from the
palette, so the strip follows the theme.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QMouseEvent, QPainter, QPaintEvent, QPalette, QPolygonF
from PySide6.QtWidgets import QSizePolicy, QWidget

from ....core.animation.timeline import Timeline

RULER, ROW, LABEL_W, DIAMOND, RIGHT = 18, 18, 110, 5, 24  # RIGHT: room for the last ruler label


def track_label(target: str) -> str:
    kind, _, name = target.partition(":")
    return {"param": name, "camera": "camera"}.get(kind, target)


def rows(timeline: Timeline) -> list[tuple[str, list[str], list[int]]]:
    """(label, track targets, key frames) per row; the camera's seven tracks share one row."""
    grouped: dict[str, tuple[list[str], set[int]]] = {}
    for track in timeline.tracks:
        targets, frames = grouped.setdefault(track_label(track.target), ([], set()))
        targets.append(track.target)
        frames.update(k.frame for k in track.keys)
    return [(label, targets, sorted(frames)) for label, (targets, frames) in grouped.items()]


class TimelineStrip(QWidget):
    scrubbed = Signal(int)  # frame
    key_menu = Signal(list, int, QPoint)  # track targets of the row, frame, global position

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.timeline, self.frame = Timeline(), 0
        self.setMinimumHeight(RULER + 2 * ROW)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(False)

    def show_timeline(self, timeline: Timeline, frame: int) -> None:
        self.timeline, self.frame = timeline, frame
        self.setMinimumHeight(RULER + max(2, len(rows(timeline))) * ROW)
        self.update()

    # -- geometry --------------------------------------------------------------------------------------------
    def _span(self) -> tuple[int, int]:
        return self.timeline.start, max(self.timeline.end, self.timeline.start + 1)

    def x_of(self, frame: float) -> float:
        start, end = self._span()
        width = max(1, self.width() - LABEL_W - DIAMOND - RIGHT)
        return LABEL_W + DIAMOND + (frame - start) / (end - start) * width

    def frame_at(self, x: float) -> int:
        start, end = self._span()
        width = max(1, self.width() - LABEL_W - DIAMOND - RIGHT)
        return max(start, min(end, round(start + (x - LABEL_W - DIAMOND) / width * (end - start))))

    def key_at(self, pos: QPointF) -> tuple[list[str], int] | None:
        index, table = int((pos.y() - RULER) // ROW), rows(self.timeline)
        if pos.y() < RULER or index >= len(table):
            return None
        _, targets, frames = table[index]
        near = [f for f in frames if abs(self.x_of(f) - pos.x()) <= DIAMOND + 2]
        return (targets, near[0]) if near else None

    # -- painting --------------------------------------------------------------------------------------------
    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()
        p.fillRect(self.rect(), pal.color(QPalette.ColorRole.Base))
        self._ruler(p, pal)
        for index, (label, _, frames) in enumerate(rows(self.timeline)):
            y = RULER + index * ROW
            p.setPen(pal.color(QPalette.ColorRole.Text))
            p.drawText(QRectF(6, y, LABEL_W - 10, ROW), Qt.AlignmentFlag.AlignVCenter, label)
            p.setBrush(pal.color(QPalette.ColorRole.Highlight))
            for frame in frames:
                self._diamond(p, self.x_of(frame), y + ROW / 2)
        x = self.x_of(self.frame)
        p.setPen(pal.color(QPalette.ColorRole.Highlight))
        p.drawLine(QPointF(x, 0), QPointF(x, self.height()))

    def _ruler(self, p: QPainter, pal: QPalette) -> None:
        start, end = self._span()
        step = next(s for s in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000) if (end - start) / s <= 12)
        p.setPen(pal.color(QPalette.ColorRole.PlaceholderText))
        for frame in range(start - start % step, end + 1, step):
            if frame >= start:
                x = self.x_of(frame)
                p.drawLine(QPointF(x, RULER - 4), QPointF(x, self.height()))
                p.drawText(QPointF(x + 2, RULER - 6), str(frame))

    @staticmethod
    def _diamond(p: QPainter, x: float, y: float) -> None:
        d = DIAMOND
        p.drawPolygon(QPolygonF([QPointF(x, y - d), QPointF(x + d, y), QPointF(x, y + d), QPointF(x - d, y)]))

    # -- mouse -----------------------------------------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        pos = event.position()
        if event.button() == Qt.MouseButton.RightButton:
            hit = self.key_at(pos)
            if hit is not None:
                self.key_menu.emit(hit[0], hit[1], event.globalPosition().toPoint())
            return
        if pos.x() >= LABEL_W:
            self.scrubbed.emit(self.frame_at(pos.x()))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.buttons() & Qt.MouseButton.LeftButton and event.position().x() >= LABEL_W:
            self.scrubbed.emit(self.frame_at(event.position().x()))
