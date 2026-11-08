"""A small stroke icon set (24×24, 2 px strokes, drawn for Structura), tinted with theme colours."""

from __future__ import annotations

from functools import cache
from pathlib import Path

import platformdirs
from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

PATHS = {
    "play": '<path d="M7 4l13 8-13 8z"/>',
    "stop": '<rect x="6" y="6" width="12" height="12" rx="2"/>',
    "zap": '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>',
    "dice": '<rect x="4" y="4" width="16" height="16" rx="3"/><circle cx="9" cy="9" r="1"/>'
    '<circle cx="15" cy="15" r="1"/><circle cx="15" cy="9" r="1"/><circle cx="9" cy="15" r="1"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "minus": '<path d="M5 12h14"/>',
    "camera": '<path d="M4 8h4l2-3h4l2 3h4v11H4z"/><circle cx="12" cy="13" r="3.5"/>',
    "image": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 17l5-5 4 4 3-3 6 6"/>'
    '<circle cx="9" cy="9" r="1.5"/>',
    "search": '<circle cx="11" cy="11" r="6"/><path d="M20 20l-4.5-4.5"/>',
    "command": '<path d="M9 6a3 3 0 1 0-3 3h12a3 3 0 1 0-3-3v12a3 3 0 1 0 3-3H6a3 3 0 1 0 3 3z"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19'
    'M5 19l1.5-1.5M17.5 6.5L19 5"/>',
    "folder": '<path d="M3 6h6l2 2h10v11H3z"/>',
    "save": '<path d="M5 4h11l3 3v13H5z"/><path d="M8 4v5h7V4M8 20v-6h8v6"/>',
    "file": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/>',
    "frame": '<path d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5"/>',
    "x": '<path d="M7 7l10 10M17 7L7 17"/>',
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5" stroke-width="3"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>',
    "layers": '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
    "activity": '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    "sphere": '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12c3 2.5 14 2.5 17 0"/><path d="M9 5.5c-2 2-2 11 0 13"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "book": '<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M4 21V5M8 7h7"/>',
    "list": '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1"/><circle cx="4.5" cy="12" r="1"/>'
    '<circle cx="4.5" cy="18" r="1"/>',
    "sliders": '<path d="M4 6h9M17 6h3M4 12h3M11 12h9M4 18h11M19 18h1"/><circle cx="15" cy="6" r="2"/>'
    '<circle cx="9" cy="12" r="2"/><circle cx="17" cy="18" r="2"/>',
    "grid": '<rect x="4" y="4" width="6.5" height="6.5" rx="1"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="1"/>'
    '<rect x="4" y="13.5" width="6.5" height="6.5" rx="1"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1"/>',
    "aperture": '<circle cx="12" cy="12" r="9"/><path d="M14.3 3.3L9.5 11.6M20.6 9.5h-9.6M18.6 17.8l-4.8-8.3'
    'M9.7 20.7l4.8-8.3M3.4 14.5h9.6M5.4 6.2l4.8 8.3"/>',
    "alert": '<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18v.5"/>',
    "terminal": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9l3 3-3 3M12 15h5"/>',
    "chart": '<path d="M4 20h16M7 16v-5M12 16V7M17 16v-8"/>',
    "film": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4"/>',
    "cube": '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M12 12l8-4.5M12 12v9M12 12L4 7.5"/>',
}


def svg(name: str, color: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{PATHS[name]}</svg>'
    )


def icon_file(name: str, color: str) -> str:
    """The icon written as an SVG file (for stylesheets, which reference images by path)."""
    folder = Path(platformdirs.user_cache_dir("structura")) / "icons"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}-{color.lstrip('#')}.svg"
    if not path.exists():
        path.write_text(svg(name, color), encoding="utf-8")
    return path.as_posix()


@cache
def icon(name: str, color: str, size: int = 18) -> QIcon:
    renderer = QSvgRenderer(QByteArray(svg(name, color).encode()))
    image = QImage(size * 2, size * 2, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    renderer.render(painter, QRectF(0, 0, size * 2, size * 2))
    painter.end()
    pixmap = QPixmap.fromImage(image)
    pixmap.setDevicePixelRatio(2.0)
    return QIcon(pixmap)
