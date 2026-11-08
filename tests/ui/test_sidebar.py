"""The left sidebar (docs/14 §2): one dock, every panel readable, no native dock-tabify conflict."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTabBar

from structura.ui.app_window import MainWindow

PANELS = ["Examples", "Outline", "Parameters", "Variations", "Render Settings"]
BOTTOM = ["Problems", "Console", "Build Stats", "Timeline", "Search"]


def test_every_sidebar_label_is_whole_and_never_elided(window: MainWindow) -> None:
    bar = window.sidebar.tabBar()
    assert [bar.tabText(i) for i in range(bar.count())] == PANELS
    assert window.sidebar.elideMode() == Qt.TextElideMode.ElideNone
    assert not bar.expanding()  # tabs keep their natural (full-label) width; overflow scrolls, not shrinks


def test_switching_panels_does_not_touch_the_dock(window: MainWindow) -> None:
    dock = window.docks["Library"]
    geometry = dock.geometry()
    window.sidebar.setCurrentWidget(window.variations)
    assert window.sidebar.currentWidget() is window.variations and dock.geometry() == geometry


def test_only_one_dock_area_uses_native_tabifying(window: MainWindow) -> None:
    """Tabifying two dock areas at once left a second, empty-looking tab bar drawn over the window on Qt
    6.12 (reproduced back to Qt 6.8, where the same spare bar exists but stays hidden and empty — a Qt
    regression, not a usage error). The sidebar avoids it by using one QTabWidget instead of dock tabifying;
    the bottom panel group is the only native one left, so this must never regress to two."""
    bars = window.findChildren(QTabBar)
    known = {window.sidebar.tabBar(), window.tabs.tabBar(), window.views.tabBar()}
    native = [b for b in bars if b not in known]
    assert len(native) == 1
    assert [native[0].tabText(i) for i in range(native[0].count())] == BOTTOM
    assert native[0].isVisible()
