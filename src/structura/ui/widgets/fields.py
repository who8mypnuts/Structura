"""Small factories for the form fields the panels and tool bars build by hand (where ParamForm does not fit):
one place for how a number box, a pair of them and a choice list are set up."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QHBoxLayout, QWidget


def spin_box(
    low: float, high: float, decimals: int = 2, name: str = "", suffix: str = "", buttons: bool = True,
    value: float | None = None,
) -> QDoubleSpinBox:  # fmt: skip
    """Returns a number box that applies on Enter or focus change, not on every typed digit.

    Args:
        low: The smallest value.
        high: The largest value.
        decimals: Digits after the point.
        name: Its accessible name (screen readers).
        suffix: A unit shown after the number (' mm', '°').
        buttons: Whether it has up/down buttons (rows of three coordinates read better without).
        value: The starting value (default: ``low``).
    """
    box = QDoubleSpinBox()
    box.setRange(low, high)
    box.setDecimals(decimals)
    box.setKeyboardTracking(False)
    box.setAccessibleName(name)
    box.setSuffix(suffix)
    if not buttons:
        box.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
    if value is not None:
        box.setValue(value)
    return box


def spin_pair(name: str, low: float, high: float, decimals: int = 3) -> tuple[QWidget, QDoubleSpinBox, QDoubleSpinBox]:
    """Returns a row of two number boxes (an x and a y).

    Args:
        name: The pair's accessible name; the boxes are '<name> x' and '<name> y'.
        low: The smallest value.
        high: The largest value.
        decimals: Digits after the point.

    Returns:
        (the row, the x box, the y box).
    """
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    x, y = spin_box(low, high, decimals, f"{name} x"), spin_box(low, high, decimals, f"{name} y")
    layout.addWidget(x)
    layout.addWidget(y)
    return row, x, y


def combo_box(items: Iterable[str], name: str = "", current: str = "", tip: str = "") -> QComboBox:
    """Returns a choice list.

    Args:
        items: The choices.
        name: Its accessible name.
        current: The choice to select (default: the first).
        tip: Its tooltip.
    """
    box = QComboBox()
    box.addItems(list(items))
    if current:
        box.setCurrentText(current)
    box.setAccessibleName(name)
    box.setToolTip(tip)
    return box
