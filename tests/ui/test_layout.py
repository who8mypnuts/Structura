"""The window fits laptop screens: bounded initial size, collapsing header, scalable panels (docs/14 §2)."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from structura.ui.app_window import MainWindow
from structura.ui.header import HeaderBar
from structura.ui.panels.variations import MIN_THUMB_WIDTH, THUMB, VariationExplorer
from structura.ui.window_geometry import initial_size

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


def test_variation_thumbnails_scale_with_the_dock(qtbot: QtBot, window: MainWindow) -> None:
    panel = VariationExplorer(window.runner)
    qtbot.addWidget(panel)
    panel.show()
    panel.resize(200, 400)
    QApplication.processEvents()
    small = panel.cells[0].iconSize().width()
    panel.resize(900, 400)
    QApplication.processEvents()
    large = panel.cells[0].iconSize().width()
    assert MIN_THUMB_WIDTH <= small < large == THUMB.width()


def test_header_drops_secondary_labels_before_primary_ones(qtbot: QtBot, window: MainWindow) -> None:
    header = HeaderBar(window.registry)  # standalone: inside the window the layout decides its width
    qtbot.addWidget(header)
    header.show()
    header.resize(header._width(1), header.height())  # room for the primary labels only
    QApplication.processEvents()
    assert header.level == 1
    style = {glyph: b.toolButtonStyle() for glyph, b in header.buttons.items()}
    assert style["play"] == style["image"] != style["dice"]


def test_the_activity_rail_shows_one_side_panel_at_a_time(window: MainWindow) -> None:
    docks, rail = window.docks, window.rail
    side = [
        "Files",
        "Examples",
        "Outline",
        "Parameters",
        "Camera",
        "Inspector",
        "Materials",
        "Lights",
        "Variations",
        "Render Settings",
    ]
    assert [b.defaultAction().objectName() for b in rail.buttons()] == [f"view.panel.{t.lower().replace(' ', '_')}"
                                                                        for t in side]  # fmt: skip
    assert all(b.toolTip() and b.accessibleName() for b in rail.buttons())  # names live in the tooltips
    assert docks["Examples"].isVisible() and not any(docks[t].isVisible() for t in side if t != "Examples")
    window.registry.trigger("view.panel.outline")
    QApplication.processEvents()
    assert docks["Outline"].isVisible() and not docks["Examples"].isVisible()
    assert window.registry.action("view.panel.outline").isChecked()
    assert not window.registry.action("view.panel.examples").isChecked()
    assert not window.tabifiedDockWidgets(docks["Outline"])  # never squeezed into tabs
    window.registry.trigger("view.panel.outline")  # the active panel's icon collapses the side bar
    QApplication.processEvents()
    assert not any(docks[t].isVisible() for t in side)


def test_tabified_bottom_panels_are_named_by_their_tabs_only(window: MainWindow) -> None:
    QApplication.processEvents()
    problems, console = window.docks["Problems"], window.docks["Console"]
    assert console in window.tabifiedDockWidgets(problems)
    assert problems.titleBarWidget() is not None  # an empty bar: the tab already says "Problems"
    assert window.docks["Examples"].titleBarWidget() is None  # a lone side panel keeps its title
    console.setFloating(True)
    QApplication.processEvents()
    assert console.titleBarWidget() is None  # a floating panel needs its title bar to be moved
    console.setFloating(False)


def test_tall_panels_scroll_instead_of_growing_the_window(window: MainWindow) -> None:
    """Showing Render Settings (a long form) used to raise the dock's minimum height past the screen, and
    QMainWindow grew the window to match."""
    size = window.size()
    for title in ("Render Settings", "Camera", "Materials", "Inspector", "Render Queue", "Timeline"):
        window.panels.show(title)
        QApplication.processEvents()
        assert window.size() == size, title
        assert window.docks[title].minimumSizeHint().height() < 200


def test_a_window_taller_than_the_screen_is_brought_back(window: MainWindow) -> None:
    screen = window.screen()
    assert screen is not None
    room = screen.availableGeometry()
    window.resize(window.width(), room.height() + 600)  # e.g. a geometry saved while a panel had grown it
    window.fit_to_screen()
    assert window.frameGeometry().height() <= max(room.height(), window.minimumSizeHint().height())
