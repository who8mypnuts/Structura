"""Viewport overlays (docs/08 §8) drawn with QPainter over either viewport (GPU or compute): the axis gizmo,
the bounding box of the structure, a HUD with the object counts, and the depth-of-field guide (the focus
plane, and the near and far limits of the sharp range, when the camera's lens has depth of field). The widget
is transparent to the mouse; orbiting and picking go to the viewport underneath."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from ...core.scene.camera import Camera
from ...preview.camera import camera_matrices
from ..i18n import tr
from ..render_view.presets import guide_rect

AXES = ((np.array([1.0, 0.0, 0.0]), "X", QColor(230, 80, 80)), (np.array([0.0, 1.0, 0.0]), "Y", QColor(110, 200, 90)),
        (np.array([0.0, 0.0, 1.0]), "Z", QColor(90, 140, 240)))  # fmt: skip
EDGES = ((0, 1), (1, 3), (3, 2), (2, 0), (4, 5), (5, 7), (7, 6), (6, 4), (0, 4), (1, 5), (2, 6), (3, 7))
GIZMO = 34  # pixels from the corner to the gizmo's centre


@dataclass(frozen=True)
class Overlays:
    axes: bool = True
    bounds: bool = False
    hud: bool = True
    focus: bool = True


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
        self.frame: tuple[float, str] | None = None  # the render frame's aspect and size label (the frame guide)
        self.stale = False  # the script has errors: the viewport shows the last good build
        self.selected: np.ndarray | None = None  # corners of the selected instance (compute preview only)
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

    def set_frame(self, aspect: float | None, label: str = "") -> None:
        """Show the render frame (a letterbox over the rest of the view); None hides it."""
        self.frame = (aspect, label) if aspect else None
        self.update()

    def _frame_guide(self, painter: QPainter) -> None:
        assert self.frame is not None
        aspect, label = self.frame
        x, y, w, h = guide_rect(aspect, (self.width(), self.height()))
        outside = QPainterPath()
        outside.addRect(QRectF(self.rect()))
        inside = QPainterPath()
        inside.addRect(QRectF(x, y, w, h))
        painter.fillPath(outside.subtracted(inside), QColor(0, 0, 0, 110))
        painter.setPen(QPen(self.accent, 1.2))
        painter.drawRect(QRectF(x, y, w, h))
        if label:
            painter.drawText(QRectF(x + 6, y + h - 22, w - 12, 18), Qt.AlignmentFlag.AlignRight, label)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        if self.camera is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.frame is not None:
            self._frame_guide(painter)
        if self.options.bounds and self.bounds is not None:
            self._bounds(painter)
        if self.selected is not None:
            self._box(painter, self.selected, QPen(self.accent, 2.0))
        if self.options.focus and self.bounds is not None and self.camera.aperture_radius > 0:
            self._focus_planes(painter)
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
        assert self.bounds is not None
        lo, hi = self.bounds
        corners = np.array([[(hi if i & 4 else lo)[0], (hi if i & 2 else lo)[1], (hi if i & 1 else lo)[2]]
                            for i in range(8)])  # fmt: skip
        self._box(painter, corners, QPen(self.accent, 1.2, Qt.PenStyle.DashLine))

    def _box(self, painter: QPainter, corners: np.ndarray, pen: QPen) -> None:
        """Eight corners (bit 2: x, bit 1: y, bit 0: z) drawn as the twelve edges of their box."""
        assert self.camera is not None
        lo, hi = self.bounds if self.bounds is not None else (corners.min(axis=0), corners.max(axis=0))
        px = project(self.camera, (self.width(), self.height()), lo, hi, corners)
        painter.setPen(pen)
        for a, b in EDGES:
            if np.isfinite(px[[a, b]]).all():
                painter.drawLine(QPointF(*px[a]), QPointF(*px[b]))

    def _plane(self, painter: QPainter, centre: np.ndarray, normal: np.ndarray, half: float, pen: QPen) -> None:
        """A square of half-size ``half`` in the plane through ``centre`` with ``normal``."""
        assert self.camera is not None and self.bounds is not None
        _, right, _ = self.camera.basis
        u = right - normal * float(np.dot(right, normal))
        u /= np.linalg.norm(u) or 1.0
        v = np.cross(normal, u)
        corners = np.array([centre + (u * a + v * b) * half for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
        px = project(self.camera, (self.width(), self.height()), *self.bounds, corners)
        if np.isfinite(px).all():
            painter.setPen(pen)
            painter.drawPolygon([QPointF(*p) for p in px])

    def _focus_planes(self, painter: QPainter) -> None:
        """The focus plane (solid, tilted with the lens) and the near / far limits of the sharp range (dashed)."""
        assert self.camera is not None and self.bounds is not None
        camera = self.camera
        forward = camera.basis[0]
        eye = np.asarray(camera.eye, np.float64)
        half = float(np.linalg.norm(self.bounds[1] - self.bounds[0])) * 0.5
        near, far = camera.sharp_range
        faint = QPen(QColor(self.accent.red(), self.accent.green(), self.accent.blue(), 120), 1.0, Qt.PenStyle.DashLine)
        for distance in (near, far):
            if 0.0 < distance < 1e12:
                self._plane(painter, eye + forward * distance, forward, half, faint)
        self._plane(painter, eye + forward * camera.focus, camera.focus_normal, half, QPen(self.accent, 1.6))

    def set_selected(self, xform: np.ndarray | None) -> None:
        """Outline this instance frame (the compute preview has no outline pass of its own); None clears."""
        if xform is None:
            self.selected = None
        else:
            unit = np.array([[(i >> 2) & 1, (i >> 1) & 1, i & 1] for i in range(8)], np.float64)
            self.selected = unit @ np.asarray(xform[:, :3], np.float64).T + np.asarray(xform[:, 3], np.float64)
        self.update()

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
