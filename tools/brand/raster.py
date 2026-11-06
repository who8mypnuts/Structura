"""Rasterise SVG strings with Qt's SVG renderer (works headless with QT_QPA_PLATFORM=offscreen)."""

from __future__ import annotations

from functools import cache
from pathlib import Path

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


@cache
def _app() -> QGuiApplication:
    existing = QGuiApplication.instance()
    return existing if isinstance(existing, QGuiApplication) else QGuiApplication([])


def render_png(svg: str, path: Path, width: int, height: int | None = None) -> None:
    _app()
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    image = QImage(width, height or width, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(painter)
    painter.end()
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(str(path))
