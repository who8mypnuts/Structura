"""A zoom-to-fit image display for progressive renders (docs/09 §9)."""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QImage, QPainter, QPaintEvent
from PySide6.QtWidgets import QWidget

from ..theming import qcolor


class ImageView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.image: QImage | None = None
        self.checker = ("#2a2a2a", "#333333")
        self.setMinimumSize(160, 120)

    def set_image(self, image: QImage | None) -> None:
        self.image = image
        self.update()

    def target_rect(self) -> QRect:
        if self.image is None:
            return QRect()
        iw, ih = self.image.width(), self.image.height()
        scale = min(self.width() / iw, self.height() / ih, 1.0 if iw <= self.width() and ih <= self.height() else 1e9)
        w, h = round(iw * scale), round(ih * scale)
        return QRect((self.width() - w) // 2, (self.height() - h) // 2, w, h)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        painter = QPainter(self)
        a, b = qcolor(self.checker[0]), qcolor(self.checker[1])
        step = 12
        for y in range(0, self.height(), step):
            for x in range(0, self.width(), step):
                painter.fillRect(x, y, step, step, a if (x // step + y // step) % 2 else b)
        if self.image is not None:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawImage(self.target_rect(), self.image)
        else:
            painter.setPen(qcolor("#999999"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Press F9 to render the current view")
