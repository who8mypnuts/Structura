"""Workspaces (docs/14 §2.1): presets on the first visit, remembered layouts afterwards, and Present."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from structura.ui.app_window import MainWindow


def _settle() -> None:
    for _ in range(3):
        QApplication.processEvents()


def test_workspaces_arrange_the_window_and_remember_changes(window: MainWindow) -> None:
    docks = window.docks
    window.registry.trigger("view.workspace_explore")
    _settle()
    assert docks["Parameters"].isVisible() and not docks["Problems"].isVisible()
    assert window.views.currentWidget() is window.viewport and window.header.workspace.text().startswith("Explore")
    window.registry.trigger("view.workspace_render")
    _settle()
    assert window.views.currentWidget() is window.render_view and docks["Render Settings"].isVisible()
    window.panels.show("Console")  # the user adds a panel to the Render workspace
    _settle()
    window.registry.trigger("view.workspace_code")
    _settle()
    assert docks["Problems"].isVisible() and docks["Examples"].isVisible()  # as it was before leaving Code
    window.registry.trigger("view.workspace_render")
    _settle()
    assert docks["Console"].isVisible()  # remembered
    assert window.registry.action("view.workspace_render").isChecked()


def test_present_hides_the_chrome_and_comes_back(window: MainWindow) -> None:
    window.registry.trigger("view.present")
    _settle()
    assert not window.menuBar().isVisible() and not window.header.isVisible() and not window.editor_area.isVisible()
    assert window.views.isVisible()
    window.workspaces.present()  # Esc
    _settle()
    assert window.menuBar().isVisible() and window.header.isVisible() and window.editor_area.isVisible()


def test_reset_layout_restores_the_default_docks(window: MainWindow) -> None:
    window.docks["Problems"].hide()
    window.panels.show("Lights")
    _settle()
    window.registry.trigger("view.reset_layout")
    _settle()
    assert window.docks["Problems"].isVisible() and not window.docks["Lights"].isVisible()
