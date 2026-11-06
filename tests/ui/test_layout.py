"""The window fits laptop screens: bounded initial size, collapsing header, scalable panels (docs/14 §2)."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from structura.ui.app_window import MainWindow, initial_size
from structura.ui.panels.variations import MIN_THUMB_WIDTH, THUMB

LAPTOP_WIDTH = 1280


def test_initial_size_fits_the_screen(window: MainWindow) -> None:
    screen = window.screen()
    assert screen is not None
    room = screen.availableGeometry().size()
    wanted = initial_size(window)
    assert wanted.width() <= room.width() and wanted.height() <= room.height()
    minimum = window.minimumSizeHint()  # a screen smaller than the minimum gets the minimum
    assert window.width() <= max(wanted.width(), minimum.width())
    assert window.height() <= max(wanted.height(), minimum.height())


def test_minimum_width_fits_a_laptop_screen(window: MainWindow) -> None:
    assert window.minimumSizeHint().width() <= LAPTOP_WIDTH


def test_header_collapses_to_icons_when_narrow_and_expands_when_wide(window: MainWindow) -> None:
    header = window.header
    window.resize(window.minimumSizeHint().width(), window.height())
    QApplication.processEvents()
    assert header.compact
    assert all(b.defaultAction().text() for b in header.buttons.values())  # names stay in tooltips
    window.resize(2400, window.height())
    QApplication.processEvents()
    assert not header.compact
    assert header.minimumSizeHint().width() < header.sizeHint().width()


def test_variation_thumbnails_scale_with_the_dock(window: MainWindow) -> None:
    panel = window.variations
    panel.resize(200, 400)
    QApplication.processEvents()
    small = panel.cells[0].iconSize().width()
    panel.resize(900, 400)
    QApplication.processEvents()
    large = panel.cells[0].iconSize().width()
    assert MIN_THUMB_WIDTH <= small < large == THUMB.width()


def test_header_drops_secondary_labels_before_primary_ones(window: MainWindow) -> None:
    header = window.header
    header.resize(header._width(1), header.height())  # room for the primary labels only
    QApplication.processEvents()
    assert header.level == 1
    style = {glyph: b.toolButtonStyle() for glyph, b in header.buttons.items()}
    assert style["play"] == style["image"] != style["dice"]
