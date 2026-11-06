"""The header bar (docs/14 §2): brand, Build, Live, seed controls, render, command palette.

Buttons show their labels when there is room. As the window narrows, the secondary buttons collapse to icons
first, then all of them (names stay in the tooltips), so the header never forces the window wider than a
laptop screen."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtGui import QPixmap, QResizeEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSpinBox, QToolButton, QWidget

from ..themes.model import Theme
from .commands.registry import CommandRegistry
from .i18n import tr
from .icons import icon

BRAND = Path(__file__).resolve().parents[1] / "resources" / "brand"
MAX_SEED = 2**31 - 1
PRIMARY = frozenset({"play", "zap", "image"})  # Build, Live Build, Render keep their labels longest
ICONS_ONLY = 2


class HeaderBar(QWidget):
    seed_changed = Signal(int)

    def __init__(self, registry: CommandRegistry, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("HeaderBar")
        self.registry = registry
        self.logo, self.title = QLabel(), QLabel("Structura")
        self.title.setObjectName("Brand")
        logo = BRAND / "png" / "icon-64.png"
        if logo.exists():
            self.logo.setPixmap(QPixmap(str(logo)).scaledToHeight(22))
        self.seed = QSpinBox()
        self.seed.setAccessibleName(tr("Seed"))
        self.seed.setRange(0, MAX_SEED)
        self.seed.setPrefix("Seed ")
        self.seed.setToolTip("Random seed (Alt+← / Alt+→)")
        self.seed.setMinimumWidth(110)  # (NoButtons + a styled border collapses Qt's inner line edit)
        self.seed.valueChanged.connect(self.seed_changed)
        self.buttons: dict[str, QToolButton] = {}
        self._widths: dict[int, int] = {}  # collapse level -> layout width (measured lazily)
        self.level = 0
        layout = self.row = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(6)
        layout.addWidget(self.logo)
        layout.addWidget(self.title)
        layout.addSpacing(16)
        for command_id, glyph in (("build.run", "play"), ("build.live", "zap")):
            layout.addWidget(self._button(command_id, glyph))
        layout.addWidget(self.seed)
        for command_id, glyph in (("build.seed_random", "dice"), ("build.seed_next", "plus")):
            layout.addWidget(self._button(command_id, glyph))
        layout.addStretch(1)
        for command_id, glyph in (("render.start", "image"), ("view.frame_all", "frame"), ("view.palette", "command")):
            layout.addWidget(self._button(command_id, glyph))

    def _button(self, command_id: str, glyph: str) -> QToolButton:
        button = QToolButton()
        button.setDefaultAction(self.registry.action(command_id))
        button.setIconSize(QSize(18, 18))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.buttons[glyph] = button
        return button

    # -- responsive labels -----------------------------------------------------------------------------------
    def _set_level(self, level: int) -> None:
        """0: every label; 1: labels on the primary buttons only; 2: icons only."""
        icon_only, with_text = Qt.ToolButtonStyle.ToolButtonIconOnly, Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        for glyph, button in self.buttons.items():
            keep = level == 0 or (level == 1 and glyph in PRIMARY)
            button.setToolButtonStyle(with_text if keep else icon_only)
        self.level = level

    def _width(self, level: int) -> int:
        """The layout's preferred width at a collapse level (measured once per font/theme)."""
        if level not in self._widths:
            current = self.level
            self._set_level(level)
            self.row.invalidate()
            self._widths[level] = self.row.sizeHint().width()
            self._set_level(current)
        return self._widths[level]

    def _fit(self) -> None:
        level = next((lv for lv in range(ICONS_ONLY) if self.width() >= self._width(lv)), ICONS_ONLY)
        if level != self.level:
            self._set_level(level)

    @property
    def compact(self) -> bool:
        """True when any label is hidden."""
        return self.level > 0

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        return QSize(self._width(ICONS_ONLY), super().minimumSizeHint().height())

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._fit()

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802
        super().changeEvent(event)
        if event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self._widths.clear()  # label widths depend on the font and the style sheet
            self.updateGeometry()
            self._fit()

    def set_theme(self, theme: Theme) -> None:
        for glyph, button in self.buttons.items():
            button.defaultAction().setIcon(icon(glyph, theme["ui.fg"]))
        self._widths.clear()
        self.updateGeometry()

    def set_seed(self, seed: int) -> None:
        self.seed.blockSignals(True)
        self.seed.setValue(seed)
        self.seed.blockSignals(False)
