"""The Render view's image display (docs/09 §9): fit or zoom (wheel, about the cursor) and pan (drag), 1:1 on
double-click, a pixel inspector (the pixel under the cursor is reported in image coordinates), an A/B split
against a snapshot, and Shift+drag to pick a region to re-render."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QImage, QMouseEvent, QPainter, QPaintEvent, QPen, QWheelEvent
from PySide6.QtWidgets import QWidget

from ..i18n import tr
from ..theming import qcolor

MIN_ZOOM, MAX_ZOOM = 0.05, 32.0


class ImageView(QWidget):
    hovered = Signal(int, int)  # image pixel under the cursor (x, y); (-1, -1) outside the image
    region_selected = Signal(QRect)  # Shift+drag: a rectangle in image pixels

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.image: QImage | None = None
        self.snapshot: QImage | None = None  # A/B: shown left of the split
        self.split = 0.5  # fraction of the width
        self.checker = ("#2a2a2a", "#333333")
        self.zoom: float | None = None  # None: fit the widget
        self.offset = QPointF(0, 0)  # pan, in widget pixels
        self._drag: QPointF | None = None
        self._region: tuple[QPointF, QPointF] | None = None
        self.setMinimumSize(160, 120)
        self.setMouseTracking(True)
        self.setAccessibleName(tr("Rendered image"))

    def set_image(self, image: QImage | None) -> None:
        self.image = image
        self.update()

    # -- geometry --------------------------------------------------------------------------------------------
    def scale(self) -> float:
        if self.image is None:
            return 1.0
        if self.zoom is not None:
            return self.zoom
        iw, ih = self.image.width(), self.image.height()
        return min(self.width() / iw, self.height() / ih, 1.0)

    def target_rect(self) -> QRectF:
        if self.image is None:
            return QRectF()
        s = self.scale()
        w, h = self.image.width() * s, self.image.height() * s
        return QRectF((self.width() - w) / 2 + self.offset.x(), (self.height() - h) / 2 + self.offset.y(), w, h)

    def image_pixel(self, pos: QPointF) -> QPoint | None:
        target = self.target_rect()
        if self.image is None or not target.contains(pos):
            return None
        s = self.scale()
        return QPoint(int((pos.x() - target.x()) / s), int((pos.y() - target.y()) / s))

    # -- painting --------------------------------------------------------------------------------------------
    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        painter = QPainter(self)
        a, b = qcolor(self.checker[0]), qcolor(self.checker[1])
        step = 12
        for y in range(0, self.height(), step):
            for x in range(0, self.width(), step):
                painter.fillRect(x, y, step, step, a if (x // step + y // step) % 2 else b)
        if self.image is None:
            painter.setPen(qcolor("#999999"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, tr("Press F9 to render the current view"))
            return
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, self.scale() < 1.0)
        target = self.target_rect()
        painter.drawImage(target, self.image)
        if self.snapshot is not None and self.snapshot.size() == self.image.size():
            self._paint_split(painter, target)
        if self._region is not None:
            painter.setPen(QPen(qcolor("#ffcc00"), 1, Qt.PenStyle.DashLine))
            painter.drawRect(QRectF(*self._region).normalized())

    def _paint_split(self, painter: QPainter, target: QRectF) -> None:
        cut = target.x() + target.width() * self.split
        left = QRectF(target.x(), target.y(), cut - target.x(), target.height())
        assert self.snapshot is not None
        source = QRectF(0, 0, self.snapshot.width() * self.split, self.snapshot.height())
        painter.drawImage(left, self.snapshot, source)
        painter.setPen(QPen(qcolor("#ffffff"), 1))
        painter.drawLine(QPointF(cut, target.top()), QPointF(cut, target.bottom()))
        painter.drawText(QPointF(target.x() + 6, target.y() + 16), "A")
        painter.drawText(QPointF(cut + 6, target.y() + 16), "B")

    # -- interaction -----------------------------------------------------------------------------------------
    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        """Zoom about the cursor."""
        if self.image is None:
            return
        old = self.scale()
        new = min(MAX_ZOOM, max(MIN_ZOOM, old * (1.25 if event.angleDelta().y() > 0 else 0.8)))
        pos, centre = event.position(), QPointF(self.width() / 2, self.height() / 2)
        self.offset = pos - (pos - centre - self.offset) * (new / old) - centre
        self.zoom = new
        self.update()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Toggle between fitting the widget and 1:1 pixels."""
        self.zoom = 1.0 if self.zoom is None else None
        self.offset = QPointF(0, 0)
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        pos = event.position()
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self._region = (pos, pos)
        elif self.snapshot is not None and abs(pos.x() - self._split_x()) < 6:
            self._drag = None
            self._region = None
            self.split = self._split_at(pos.x())
        else:
            self._drag = pos
        self.update()

    def _split_x(self) -> float:
        target = self.target_rect()
        return target.x() + target.width() * self.split

    def _split_at(self, x: float) -> float:
        target = self.target_rect()
        return min(1.0, max(0.0, (x - target.x()) / max(target.width(), 1.0)))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        pos = event.position()
        pixel = self.image_pixel(pos)
        self.hovered.emit(*((pixel.x(), pixel.y()) if pixel is not None else (-1, -1)))
        if self._region is not None and event.buttons():
            self._region = (self._region[0], pos)
        elif self._drag is not None and event.buttons():
            self.offset += pos - self._drag
            self._drag = pos
        elif self.snapshot is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.split = self._split_at(pos.x())
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._region is not None:
            a, b = (self.image_pixel(p) for p in self._region)
            self._region = None
            if a is not None and b is not None and a != b:
                self.region_selected.emit(QRect(a, b).normalized())
        self._drag = None
        self.update()
