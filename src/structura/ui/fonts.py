"""Register the bundled fonts (Inter, JetBrains Mono; OFL) with Qt (docs/13 §9)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase

FONTS = Path(__file__).resolve().parents[1] / "resources" / "fonts"
UI_FAMILY, CODE_FAMILY = "Inter", "JetBrains Mono"


def register_fonts() -> list[str]:
    families: list[str] = []
    for path in sorted(FONTS.rglob("*.[ot]tf")):
        font_id = QFontDatabase.addApplicationFont(str(path))
        families += QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
    return sorted(set(families))


def code_font(size: int = 11) -> QFont:
    font = QFont(CODE_FAMILY, size)
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setFixedPitch(True)
    return font
