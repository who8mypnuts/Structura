"""Accessibility (docs/14 §8, docs/18 §7): every focusable widget has an accessible name."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAccessible
from PySide6.QtWidgets import QAbstractSpinBox, QComboBox, QWidget

from structura.core.animation.timeline import Timeline
from structura.ui.app_window import MainWindow
from structura.ui.dialogs.animation_dialog import AnimationDialog
from structura.ui.dialogs.preferences import PreferencesDialog


def _internal(widget: QWidget) -> bool:
    """Qt's own parts: a spin box's line edit, a combo box's popup list."""
    parent = widget.parentWidget()
    while parent is not None:
        if isinstance(parent, QAbstractSpinBox | QComboBox):
            return True
        parent = parent.parentWidget()
    return type(widget).__name__ == "QListView" and widget.parentWidget().__class__.__name__ == "QFrame"


def unnamed(root: QWidget) -> list[str]:
    out = []
    for widget in [root, *root.findChildren(QWidget)]:
        if widget.focusPolicy() == Qt.FocusPolicy.NoFocus or _internal(widget):
            continue
        iface = QAccessible.queryAccessibleInterface(widget)
        if iface is None or not iface.text(QAccessible.Text.Name).strip():
            out.append(f"{type(widget).__name__} in {type(widget.parentWidget()).__name__}")
    return out


def test_main_window_and_dialogs_name_every_focusable_widget(window: MainWindow) -> None:
    window.docs.new_script()
    assert unnamed(window) == []
    assert unnamed(PreferencesDialog(window.settings, window)) == []
    from structura.ui.dialogs.render_output import RenderOutputDialog  # noqa: PLC0415
    from structura.ui.save_paths import SavePaths  # noqa: PLC0415

    final = RenderOutputDialog(SavePaths(window.settings), Path("a.png"), "Final", "Render", ("Final",), window)
    assert unnamed(final) == []
    assert unnamed(AnimationDialog(Timeline(), window.settings.directory(), window)) == []
