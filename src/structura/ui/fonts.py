"""Register the bundled fonts (Inter, JetBrains Mono; OFL) with Qt (docs/13 §9)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QWidget

FONTS = Path(__file__).resolve().parents[1] / "resources" / "fonts"
UI_FAMILY, CODE_FAMILY = "Inter", "JetBrains Mono"
_chosen = {"ui": UI_FAMILY, "code": CODE_FAMILY}  # the Preferences' choices (appearance/ui_font, editor/code_font)


def register_fonts() -> list[str]:
    families: list[str] = []
    for path in sorted(FONTS.rglob("*.[ot]tf")):
        font_id = QFontDatabase.addApplicationFont(str(path))
        families += QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
    return sorted(set(families))


def choose_families(ui: str, code: str) -> None:
    """Set the interface and code families; "System" means the platform's general font, an unknown code
    family falls back to the bundled JetBrains Mono."""
    system = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont).family()
    _chosen["ui"] = system if ui == "System" else (ui or UI_FAMILY)
    _chosen["code"] = code if code and code in QFontDatabase.families() else CODE_FAMILY


def ui_family() -> str:
    return _chosen["ui"]


def code_family() -> str:
    return _chosen["code"]


def code_font(size: int = 11) -> QFont:
    font = QFont(code_family(), size)
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setFixedPitch(True)
    return font


def use_code_font(widget: QWidget, size: int = 10) -> None:
    """Show ``widget`` in the code font. A widget style sheet outranks the application's, whose QWidget rule
    sets the interface font for everything."""
    widget.setStyleSheet(f'font-family: "{code_family()}"; font-size: {size}pt;')
    widget.setFont(code_font(size))
