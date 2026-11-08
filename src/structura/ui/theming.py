"""Apply a resolved Theme to Qt: QPalette (Fusion), the generated stylesheet and editor text formats."""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette, QTextCharFormat
from PySide6.QtWidgets import QApplication

from ..themes.expr import split_alpha
from ..themes.model import Theme
from ..themes.qss import Fonts, render_qss
from .icons import icon_file


def qcolor(value: str) -> QColor:
    rgb, alpha = split_alpha(value)
    color = QColor(rgb)
    color.setAlphaF(alpha)
    return color


PALETTE_ROLES: dict[QPalette.ColorRole, str] = {
    QPalette.ColorRole.Window: "ui.bg",
    QPalette.ColorRole.WindowText: "ui.fg",
    QPalette.ColorRole.Base: "ui.bg.sunken",
    QPalette.ColorRole.AlternateBase: "ui.bg.alt",
    QPalette.ColorRole.ToolTipBase: "ui.bg.raised",
    QPalette.ColorRole.ToolTipText: "ui.fg",
    QPalette.ColorRole.PlaceholderText: "ui.fg.muted",
    QPalette.ColorRole.Text: "ui.fg",
    QPalette.ColorRole.Button: "ui.bg.raised",
    QPalette.ColorRole.ButtonText: "ui.fg",
    QPalette.ColorRole.BrightText: "status.error",
    QPalette.ColorRole.Highlight: "ui.accent",
    QPalette.ColorRole.HighlightedText: "ui.accent.fg",
    QPalette.ColorRole.Link: "ui.link",
}


def palette(theme: Theme) -> QPalette:
    pal = QPalette()
    for role, name in PALETTE_ROLES.items():
        pal.setColor(role, qcolor(theme[name]))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
        pal.setColor(QPalette.ColorGroup.Disabled, role, qcolor(theme["ui.fg.disabled"]))
    return pal


def apply_theme(app: QApplication, theme: Theme, fonts: Fonts | None = None, density: str = "comfortable") -> None:
    if app.style().name().lower() != "fusion":  # setting it again re-polishes every widget for nothing
        app.setStyle("Fusion")
    app.setPalette(palette(theme))
    assets = {"close": icon_file("x", split_alpha(theme["ui.fg.muted"])[0]),
              "check": icon_file("check", split_alpha(theme["ui.accent.fg"])[0]),
              "tick": icon_file("check", split_alpha(theme["ui.fg"])[0])}  # fmt: skip
    app.setStyleSheet(render_qss(theme, fonts, density, assets=assets))


def syntax_format(theme: Theme, role: str) -> QTextCharFormat:
    """The QTextCharFormat of a syntax role (role without or with the 'syntax.' prefix)."""
    style = theme.style(role if role.startswith("syntax.") else f"syntax.{role}")
    fmt = QTextCharFormat()
    fmt.setForeground(qcolor(style.color))
    if style.bold:
        fmt.setFontWeight(QFont.Weight.DemiBold)
    fmt.setFontItalic(style.italic)
    if style.underline:
        fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SingleUnderline)
    return fmt
