"""Viewport overlays (docs/08 §8) drawn with QPainter over either viewport (GPU or compute): the axis gizmo,
the bounding box of the structure and a HUD with the object counts. The widget is transparent to the mouse;
orbiting and picking go to the viewport underneath."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from ...core.scene.camera import Camera
from ...preview.camera import camera_matrices
from ..i18n import tr

AXES = ((np.array([1.0, 0.0, 0.0]), "X", QColor(230, 80, 80)), (np.array([0.0, 1.0, 0.0]), "Y", QColor(110, 200, 90)),
        (np.array([0.0, 0.0, 1.0]), "Z", QColor(90, 140, 240)))  # fmt: skip
EDGES = ((0, 1), (1, 3), (3, 2), (2, 0), (4, 5), (5, 7), (7, 6), (6, 4), (0, 4), (1, 5), (2, 6), (3, 7))
GIZMO = 34  # pixels from the corner to the gizmo's centre


@dataclass(frozen=True)
class Overlays:
    axes: bool = True
    bounds: bool = False
    hud: bool = True


def project(camera: Camera, size: tuple[int, int], lo: np.ndarray, hi: np.ndarray, points: np.ndarray) -> np.ndarray:
    """World points → widget pixels (x right, y down); rows behind the camera are NaN."""
    m = camera_matrices(camera, size[0] / max(1, size[1]), lo, hi)
    clip = (m.proj @ m.view @ np.c_[points, np.ones(len(points))].T).T
    w = clip[:, 3:4]
    ndc = np.where(w > 1e-9, clip[:, :2] / np.where(w > 1e-9, w, 1.0), np.nan)
    pixels: np.ndarray = np.c_[(ndc[:, 0] + 1) / 2 * size[0], (1 - ndc[:, 1]) / 2 * size[1]]
    return pixels


class ViewportOverlay(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.options = Overlays()
        self.camera: Camera | None = None
        self.bounds: tuple[np.ndarray, np.ndarray] | None = None
        self.hud = ""
        self.stale = False  # the script has errors: the viewport shows the last good build
        self.accent = QColor(255, 158, 38)

    def show_state(self, camera: Camera | None, bounds: tuple[np.ndarray, np.ndarray] | None, hud: str) -> None:
        self.camera, self.bounds, self.hud = camera, bounds, hud
        self.update()

    def set_stale(self, stale: bool) -> None:
        if stale != self.stale:
            self.stale = stale
            self.update()

    def set_camera(self, camera: Camera) -> None:
        self.camera = camera
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        if self.camera is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.options.bounds and self.bounds is not None:
            self._bounds(painter)
        if self.options.axes:
            self._axes(painter)
        if self.options.hud and self.hud:
            self._hud(painter)
        if self.stale:
            self._badge(painter, "⚠  " + tr("Last good build: the script has errors"), 40)
        painter.end()

    def _badge(self, painter: QPainter, text: str, top: int) -> None:
        metrics = painter.fontMetrics()
        box = QRectF(8, top, metrics.horizontalAdvance(text) + 24, metrics.height() + 8)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(180, 110, 20, 220))
        painter.drawRoundedRect(box, 8, 8)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(box, Qt.AlignmentFlag.AlignCenter, text)

    def _bounds(self, painter: QPainter) -> None:
        assert self.camera is not None and self.bounds is not None
        lo, hi = self.bounds
        corners = np.array([[(hi if i & 4 else lo)[0], (hi if i & 2 else lo)[1], (hi if i & 1 else lo)[2]]
                            for i in range(8)])  # fmt: skip
        px = project(self.camera, (self.width(), self.height()), lo, hi, corners)
        pen = QPen(self.accent, 1.2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        for a, b in EDGES:
            if np.isfinite(px[[a, b]]).all():
                painter.drawLine(QPointF(*px[a]), QPointF(*px[b]))

    def _axes(self, painter: QPainter) -> None:
        """The world axes as the camera sees them, in the bottom-left corner (orientation only)."""
        assert self.camera is not None
        forward, right, up = self.camera.basis
        centre = QPointF(GIZMO, self.height() - GIZMO)
        ordered = sorted(AXES, key=lambda axis: float(np.dot(axis[0], forward)), reverse=True)  # far ones first
        font = QFont(self.font())
        font.setBold(True)
        painter.setFont(font)
        for direction, name, colour in ordered:
            end = centre + QPointF(float(np.dot(direction, right)), -float(np.dot(direction, up))) * (GIZMO * 0.7)
            painter.setPen(QPen(colour, 2.0))
            painter.drawLine(centre, end)
            painter.drawText(QRectF(end.x() - 8, end.y() - 8, 16, 16), Qt.AlignmentFlag.AlignCenter, name)

    def _hud(self, painter: QPainter) -> None:
        metrics = painter.fontMetrics()
        box = QRectF(0, 0, metrics.horizontalAdvance(self.hud) + 20, metrics.height() + 8)
        box.moveTopRight(QPointF(self.width() - 8, 8))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 130))
        painter.drawRoundedRect(box, 8, 8)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(box, Qt.AlignmentFlag.AlignCenter, self.hud)
